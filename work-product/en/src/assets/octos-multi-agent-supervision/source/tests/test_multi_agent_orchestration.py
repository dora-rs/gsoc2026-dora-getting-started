import json
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

import tools.run_octos_multi_agent as orchestration
from tools.run_octos_multi_agent import (
    BASELINE_POLICY_SOURCE,
    activate_supervisor_strategy,
    EventLog,
    OctosAgent,
    build_policy_context,
    merge_observation,
    observation_prompt,
    operator_actions_prompt,
    prepare_agents_concurrently,
    reconcile_switch_state,
    shutdown_switch_actions,
    should_review_strategy,
    strategy_authoring_prompt,
    strategy_correction_prompt,
    strategy_review_prompt,
    sync_octos_skill,
    unload_ollama_model,
)
from process_runtime.adaptive_policy import (
    run_strategy,
    save_strategy_version,
    validate_strategy_replays,
)
from process_runtime.octos_protocol import StrategyProposal


class ConcurrentAgent:
    def __init__(
        self,
        own_started: threading.Event,
        other_started: threading.Event,
        result: dict,
    ) -> None:
        self.own_started = own_started
        self.other_started = other_started
        self.result = result

    def ask(self, _prompt: str) -> dict:
        self.own_started.set()
        if not self.other_started.wait(timeout=1.0):
            raise RuntimeError("the other robot agent did not start concurrently")
        return self.result


def test_strategy_review_waits_for_three_complete_cycles() -> None:
    assert not should_review_strategy(1)
    assert not should_review_strategy(2)
    assert should_review_strategy(3)
    assert not should_review_strategy(4)
    assert should_review_strategy(6)


def test_agent_preparation_overlaps_observer_and_operator() -> None:
    observer_started = threading.Event()
    operator_started = threading.Event()
    observer = ConcurrentAgent(
        observer_started,
        operator_started,
        {
            "role": "observer",
            "location": "station",
            "docked": True,
            "pressure_kpa": 172.0,
            "pressure_observed_at_s": 11.0,
            "temperature_c": 44.0,
            "temperature_observed_at_s": 10.0,
            "temperature_visible": True,
            "temperature_confidence": 1.0,
            "temperature_image": "frame.jpg",
            "model": "qwen3-vl:8b-instruct",
        },
    )
    operator = ConcurrentAgent(
        operator_started,
        observer_started,
        {
            "role": "operator",
            "location": "station",
            "at_control": True,
            "cooling_on": False,
            "relief_open": False,
        },
    )

    observation, operator_state = prepare_agents_concurrently(
        observer,
        operator,
    )

    assert observation["pressure_kpa"] == 172.0
    assert operator_state["at_control"] is True


def test_strategy_authoring_prompt_gives_freedom_without_fixed_policy() -> None:
    prompt = strategy_authoring_prompt(
        [
            {
                "temperature_c": 44.0,
                "temperature_observed_at_s": 10.0,
                "pressure_kpa": 172.0,
                "pressure_observed_at_s": 11.0,
            }
        ]
    )

    assert "def decide(context)" in prompt
    assert "30-60 C" in prompt
    assert "160-200 kPa" in prompt
    assert "choose observation timing" in prompt
    assert "revise" in prompt
    assert "+0.25 C/s" in prompt
    assert "+0.32 kPa/s" in prompt
    assert "never be empty" in prompt
    assert '"temperature":0.0' in prompt
    assert '"pressure":0.0' in prompt
    assert "independent if statements" in prompt
    assert 'latest = context["history"][-1]' in prompt
    assert "no current top-level" in prompt
    assert "temperature_c" in prompt and "pressure_kpa" in prompt
    assert BASELINE_POLICY_SOURCE in prompt
    for fixed_policy in (
        "2 through 12",
        "55-58 C",
        "185-195 kPa",
        "temperature_control_due",
        "recommended disable",
        "finite mission",
    ):
        assert fixed_policy not in prompt


def test_observation_prompt_requests_only_selected_sensors() -> None:
    pressure_prompt = observation_prompt(["pressure"], wait_seconds=9)
    temperature_prompt = observation_prompt(
        ["temperature_rgb"],
        wait_seconds=4,
    )

    assert "seconds=9" in pressure_prompt
    assert "read_pressure exactly once" in pressure_prompt
    assert "read_temperature exactly once" not in pressure_prompt
    assert "get_status exactly once" in pressure_prompt
    assert '"cooling_on":false' in pressure_prompt
    assert '"relief_open":false' in pressure_prompt
    assert "seconds=4" in temperature_prompt
    assert "read_temperature exactly once" in temperature_prompt
    assert "read_pressure exactly once" not in temperature_prompt
    assert "get_status exactly once" in temperature_prompt


def test_operator_prompt_applies_immediate_idempotent_actions() -> None:
    prompt = operator_actions_prompt(
        "adaptive-cycle-1-open",
        [{"switch": "cooling", "enabled": True}],
    )

    assert "apply_switch_actions exactly once" in prompt
    assert '"action_id":"adaptive-cycle-1-open"' in prompt
    assert '"enabled":true' in prompt
    assert "execute_control_plan" not in prompt
    assert "disable_after_seconds" not in prompt


def test_partial_observation_keeps_last_sensor_value_and_timestamp() -> None:
    previous = {
        "temperature_c": 45.0,
        "temperature_observed_at_s": 12.0,
        "pressure_kpa": 174.0,
        "pressure_observed_at_s": 12.5,
    }

    merged = merge_observation(
        previous,
        {
            "pressure_kpa": 178.0,
            "pressure_observed_at_s": 18.5,
        },
    )

    assert merged == {
        "temperature_c": 45.0,
        "temperature_observed_at_s": 12.0,
        "pressure_kpa": 178.0,
        "pressure_observed_at_s": 18.5,
    }


def test_observed_process_state_reconciles_automatic_valve_shutdown() -> None:
    reconciled = reconcile_switch_state(
        {"cooling": True, "relief": True},
        {"cooling_on": False, "relief_open": False},
    )

    assert reconciled == {"cooling": False, "relief": False}


def test_missing_process_state_preserves_current_switch_state() -> None:
    reconciled = reconcile_switch_state(
        {"cooling": True, "relief": False},
        {"pressure_kpa": 180.0},
    )

    assert reconciled == {"cooling": True, "relief": False}


def test_shutdown_closes_only_switches_still_marked_active() -> None:
    assert shutdown_switch_actions(
        {"cooling": True, "relief": False}
    ) == [{"switch": "cooling", "enabled": False}]
    assert shutdown_switch_actions(
        {"cooling": True, "relief": True}
    ) == [
        {"switch": "cooling", "enabled": False},
        {"switch": "relief", "enabled": False},
    ]
    assert shutdown_switch_actions(
        {"cooling": False, "relief": False}
    ) == []


def test_policy_context_contains_history_rates_and_current_state() -> None:
    history = [
        {
            "temperature_c": 44.0,
            "temperature_observed_at_s": 10.0,
            "pressure_kpa": 172.0,
            "pressure_observed_at_s": 10.0,
        },
        {
            "temperature_c": 46.2,
            "temperature_observed_at_s": 20.0,
            "pressure_kpa": 178.5,
            "pressure_observed_at_s": 20.0,
        },
    ]

    context = build_policy_context(
        history,
        {"cooling": False, "relief": True},
        completed_cycles=1,
    )

    assert context["history"] == history
    assert context["rates"] == {
        "temperature_c_per_s": pytest.approx(0.22),
        "pressure_kpa_per_s": pytest.approx(0.65),
    }
    assert context["switch_state"] == {
        "cooling": False,
        "relief": True,
    }
    assert context["completed_cycles"] == 1
    assert context["normal_ranges"] == {
        "temperature_c": [30.0, 60.0],
        "pressure_kpa": [160.0, 200.0],
    }


def test_strategy_review_prompt_can_keep_or_revise_source() -> None:
    prompt = strategy_review_prompt(
        "def decide(context):\n    return {}\n",
        {"completed_cycles": 1, "history": []},
    )

    assert "keep it unchanged or revise it" in prompt
    assert "completed_cycles" in prompt
    assert "strategy_source" in prompt


def test_invalid_strategy_is_returned_to_supervisor_for_revision(
    tmp_path: Path,
) -> None:
    valid_source = """
def decide(context):
    latest = context["history"][-1]
    switches = context["switch_state"]
    actions = []
    if latest["temperature_c"] >= 40.0 and not switches["cooling"]:
        actions = actions + [{"switch": "cooling", "enabled": True}]
    if latest["pressure_kpa"] >= 170.0 and not switches["relief"]:
        actions = actions + [{"switch": "relief", "enabled": True}]
    if latest["temperature_c"] <= 34.0 and switches["cooling"]:
        actions = actions + [{"switch": "cooling", "enabled": False}]
    if latest["pressure_kpa"] <= 165.0 and switches["relief"]:
        actions = actions + [{"switch": "relief", "enabled": False}]
    return {
        "observe": ["pressure", "temperature_rgb"],
        "actions": actions,
        "observe_after_seconds": 6,
        "reason": "adaptive safe-range control",
    }
"""

    class FakeSupervisor:
        def __init__(self) -> None:
            self.prompts: list[str] = []
            self.proposals = [
                StrategyProposal(
                    source="import os\ndef decide(context): return {}",
                    reason="invalid first attempt",
                ),
                StrategyProposal(
                    source=valid_source,
                    reason="corrected strategy",
                ),
            ]

        def ask(self, prompt: str, *, expect_strategy: bool):
            assert expect_strategy is True
            self.prompts.append(prompt)
            return self.proposals.pop(0)

    context = build_policy_context(
        [
            {
                "temperature_c": 48.0,
                "temperature_observed_at_s": 10.0,
                "pressure_kpa": 180.0,
                "pressure_observed_at_s": 10.0,
            }
        ],
        {"cooling": False, "relief": False},
        completed_cycles=0,
    )
    event_log = EventLog(tmp_path / "events")
    supervisor = FakeSupervisor()

    path, proposal = activate_supervisor_strategy(
        supervisor,
        initial_prompt="author a strategy",
        policy_dir=tmp_path / "policies",
        context=context,
        event_log=event_log,
        version=1,
    )

    assert path.is_file()
    assert proposal.reason == "corrected strategy"
    assert len(supervisor.prompts) == 2
    assert "strategy may only contain the decide function" in supervisor.prompts[1]
    assert (
        "cooling and relief are the only switches"
        in supervisor.prompts[1].lower()
    )


def test_observation_validation_error_gets_executable_repair_hint() -> None:
    prompt = strategy_correction_prompt(
        "author a strategy",
        "def decide(context): return {}",
        "observe must be a non-empty sensor list",
    )

    assert "Change the executable source" in prompt
    assert "if not observe_list:" in prompt
    assert 'observe_list = ["pressure", "temperature_rgb"]' in prompt


def test_freshness_type_error_gets_nested_dictionary_repair_hint() -> None:
    prompt = strategy_correction_prompt(
        "author a strategy",
        "def decide(context): return {}",
        "TypeError: '>' not supported between instances of 'dict' and 'int' "
        "at freshness_seconds > 60",
    )

    assert (
        'freshness_seconds["temperature"]' in prompt
        and 'freshness_seconds["pressure"]' in prompt
    )
    assert "comparison between freshness_seconds itself and a number" in prompt


def test_replay_errors_get_executable_history_access_patterns() -> None:
    upper = strategy_correction_prompt(
        "author",
        "def decide(context): return {}",
        "upper-range replay must enable cooling and relief",
    )
    lower = strategy_correction_prompt(
        "author",
        "def decide(context): return {}",
        "lower-range replay must disable cooling and relief",
    )

    for prompt in (upper, lower):
        assert 'latest = context["history"][-1]' in prompt
        assert 'latest["temperature_c"]' in prompt
        assert 'latest["pressure_kpa"]' in prompt
    assert 'rates["temperature_c_per_s"] > 0' in upper
    assert 'rates["pressure_kpa_per_s"] > 0' in upper
    assert 'rates["temperature_c_per_s"] < 0' in lower
    assert 'rates["pressure_kpa_per_s"] < 0' in lower


def test_verified_baseline_strategy_passes_replays(tmp_path: Path) -> None:
    path = save_strategy_version(
        BASELINE_POLICY_SOURCE,
        tmp_path,
        version=1,
    )

    validate_strategy_replays(path)


def test_verified_baseline_acts_with_agent_latency_margin(
    tmp_path: Path,
) -> None:
    path = save_strategy_version(
        BASELINE_POLICY_SOURCE,
        tmp_path,
        version=1,
    )
    context = build_policy_context(
        [
            {
                "temperature_c": 40.0,
                "temperature_observed_at_s": 60.0,
                "pressure_kpa": 170.0,
                "pressure_observed_at_s": 48.0,
            }
        ],
        {"cooling": False, "relief": False},
        completed_cycles=0,
    )

    decision = run_strategy(path, context)

    assert decision["actions"] == [
        {"switch": "cooling", "enabled": True},
        {"switch": "relief", "enabled": True},
    ]


def test_invalid_supervisor_candidates_fall_back_to_verified_baseline(
    tmp_path: Path,
) -> None:
    class InvalidSupervisor:
        def ask(self, _prompt: str, *, expect_strategy: bool):
            assert expect_strategy is True
            return StrategyProposal(
                source="def decide(context): return {}",
                reason="invalid candidate",
            )

    context = build_policy_context(
        [
            {
                "temperature_c": 48.0,
                "temperature_observed_at_s": 10.0,
                "pressure_kpa": 180.0,
                "pressure_observed_at_s": 10.0,
            }
        ],
        {"cooling": False, "relief": False},
        completed_cycles=0,
    )
    event_log = EventLog(tmp_path / "events")

    path, proposal = activate_supervisor_strategy(
        InvalidSupervisor(),
        initial_prompt="adapt the baseline",
        policy_dir=tmp_path / "policies",
        context=context,
        event_log=event_log,
        version=1,
        max_attempts=2,
    )

    assert path.read_text(encoding="utf-8") == BASELINE_POLICY_SOURCE
    assert proposal.source == BASELINE_POLICY_SOURCE
    assert "strategy_fallback_activated" in event_log.path.read_text(
        encoding="utf-8"
    )


def test_operator_uses_execution_receipt_when_final_text_is_invalid(
    monkeypatch,
    tmp_path: Path,
) -> None:
    receipt = tmp_path / "adaptive-cycle-1-open.json"

    def fake_run(*_args, **_kwargs):
        receipt.write_text(
            json.dumps(
                {
                    "action_id": "adaptive-cycle-1-open",
                    "events": [],
                    "all_succeeded": True,
                }
            ),
            encoding="utf-8",
        )
        return SimpleNamespace(
            returncode=0,
            stdout='{"text":"not valid JSON"}',
            stderr="",
        )

    monkeypatch.setattr(orchestration.subprocess, "run", fake_run)
    output_dir = tmp_path / "agent"
    event_log = EventLog(output_dir)
    operator = OctosAgent(
        "Operator",
        octos=tmp_path / "octos",
        output_dir=output_dir,
        event_log=event_log,
    )

    result = operator.ask("execute it", execution_receipt=receipt)

    assert result["action_id"] == "adaptive-cycle-1-open"
    assert result["all_succeeded"] is True


def test_octos_agent_uses_its_assigned_model(
    monkeypatch,
    tmp_path: Path,
) -> None:
    receipt = tmp_path / "receipt.json"
    receipt.write_text(
        json.dumps({"all_succeeded": True, "events": []}),
        encoding="utf-8",
    )
    captured: dict[str, list[str]] = {}

    def fake_run(command, **_kwargs):
        captured["command"] = command
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(orchestration.subprocess, "run", fake_run)
    agent = OctosAgent(
        "Supervisor",
        octos=tmp_path / "octos",
        output_dir=tmp_path / "agent",
        event_log=EventLog(tmp_path / "agent"),
        model="qwen2.5-coder:7b",
    )

    agent.ask("author", execution_receipt=receipt)

    command = captured["command"]
    assert command[command.index("--model") + 1] == "qwen2.5-coder:7b"


def test_unload_ollama_model_stops_only_the_selected_model(
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(orchestration.subprocess, "run", fake_run)

    unload_ollama_model(
        "qwen3-vl:8b-instruct",
        ollama=Path("/opt/ollama"),
    )

    assert captured["command"] == [
        str(Path("/opt/ollama")),
        "stop",
        "qwen3-vl:8b-instruct",
    ]
    assert captured["kwargs"]["check"] is False


def test_sync_octos_skill_replaces_stale_installed_copy(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    installed = tmp_path / ".octos" / "skills" / "process-supervision"
    source.mkdir()
    installed.mkdir(parents=True)
    (source / "manifest.json").write_text("new manifest", encoding="utf-8")
    (source / "main").write_text("new main", encoding="utf-8")
    (source / "SKILL.md").write_text("new skill", encoding="utf-8")
    (installed / "manifest.json").write_text("stale", encoding="utf-8")

    target = sync_octos_skill(source_skill=source, workspace=tmp_path)

    assert target == installed
    assert (target / "manifest.json").read_text(encoding="utf-8") == "new manifest"
    assert (target / "main").read_text(encoding="utf-8") == "new main"
