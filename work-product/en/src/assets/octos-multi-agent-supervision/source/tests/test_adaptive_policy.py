from pathlib import Path

import pytest

from process_runtime.adaptive_policy import (
    run_strategy,
    save_strategy_version,
    validate_strategy_replays,
    validate_strategy_decision,
    validate_strategy_source,
)


SAFE_STRATEGY = """
def decide(context):
    latest = context["history"][-1]
    if latest["temperature_c"] >= 56.0:
        return {
            "observe": ["pressure", "temperature_rgb"],
            "actions": [{"switch": "cooling", "enabled": True}],
            "observe_after_seconds": 6,
            "reason": "temperature is approaching the upper range",
        }
    return {
        "observe": ["pressure"],
        "actions": [],
        "observe_after_seconds": 10,
        "reason": "continue sampling the pressure trend",
    }
"""


def context(*, temperature_c: float = 55.0) -> dict:
    return {
        "history": [
            {
                "temperature_c": temperature_c,
                "pressure_kpa": 184.0,
                "observed_at_s": 12.0,
            }
        ],
        "switch_state": {"cooling": False, "relief": False},
        "normal_ranges": {
            "temperature_c": [30.0, 60.0],
            "pressure_kpa": [160.0, 200.0],
        },
    }


def test_strategy_accepts_pure_trend_based_decision() -> None:
    validate_strategy_source(SAFE_STRATEGY)


def test_strategy_allows_safe_local_iteration_and_list_building() -> None:
    validate_strategy_source(
        """
def decide(context):
    sensors = []
    for item in reversed(context["history"]):
        if item.get("temperature_c") is not None:
            sensors.append("temperature_rgb")
    return {
        "observe": sensors,
        "actions": [],
        "observe_after_seconds": 5,
        "reason": "fresh local history scan",
    }
"""
    )


@pytest.mark.parametrize(
    "source",
    [
        "import os\ndef decide(context): return {}",
        "def decide(context):\n    open('x', 'w')",
        "def decide(context):\n    return __import__('socket')",
        "def decide(context):\n    while True:\n        pass",
    ],
)
def test_strategy_rejects_external_side_effects_and_unbounded_loops(
    source: str,
) -> None:
    with pytest.raises(ValueError):
        validate_strategy_source(source)


def test_strategy_requires_one_decide_function() -> None:
    with pytest.raises(ValueError, match="decide"):
        validate_strategy_source("answer = 42")


def test_strategy_version_is_saved_atomically(tmp_path: Path) -> None:
    path = save_strategy_version(SAFE_STRATEGY, tmp_path, version=3)

    assert path == tmp_path / "strategy-v003.py"
    assert path.read_text(encoding="utf-8") == SAFE_STRATEGY
    assert not (tmp_path / "strategy-v003.py.tmp").exists()


def test_strategy_runs_in_isolated_process(tmp_path: Path) -> None:
    path = save_strategy_version(SAFE_STRATEGY, tmp_path, version=1)

    decision = run_strategy(path, context(temperature_c=57.0))

    assert decision == {
        "observe": ["pressure", "temperature_rgb"],
        "actions": [{"switch": "cooling", "enabled": True}],
        "observe_after_seconds": 6,
        "reason": "temperature is approaching the upper range",
    }


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("observe", ["hidden_truth"], "sensor"),
        (
            "actions",
            [{"switch": "alarm", "enabled": True}],
            "switch",
        ),
        ("observe_after_seconds", 0, "between 1 and 120"),
        ("observe_after_seconds", 121, "between 1 and 120"),
        ("reason", "", "reason"),
    ],
)
def test_strategy_decision_rejects_invalid_contract(
    field: str,
    value: object,
    message: str,
) -> None:
    decision = {
        "observe": ["pressure"],
        "actions": [],
        "observe_after_seconds": 8,
        "reason": "sample again",
    }
    decision[field] = value

    with pytest.raises(ValueError, match=message):
        validate_strategy_decision(decision, context())


def test_strategy_cannot_enable_control_at_normal_lower_bound() -> None:
    decision = {
        "observe": ["pressure", "temperature_rgb"],
        "actions": [
            {"switch": "cooling", "enabled": True},
            {"switch": "relief", "enabled": True},
        ],
        "observe_after_seconds": 5,
        "reason": "incorrectly enable controls",
    }
    unsafe_context = context(temperature_c=30.0)
    unsafe_context["history"][-1]["pressure_kpa"] = 160.0

    with pytest.raises(ValueError, match="lower bound"):
        validate_strategy_decision(decision, unsafe_context)


REPLAY_CAPABLE_STRATEGY = """
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
        "reason": "rate-aware boundary control",
    }
"""


def test_strategy_replays_confirm_upper_and_lower_control_ability(
    tmp_path: Path,
) -> None:
    path = save_strategy_version(
        REPLAY_CAPABLE_STRATEGY,
        tmp_path,
        version=1,
    )

    validate_strategy_replays(path)


def test_strategy_replays_reject_policy_that_never_controls(
    tmp_path: Path,
) -> None:
    path = save_strategy_version(
        """
def decide(context):
    return {
        "observe": ["pressure"],
        "actions": [],
        "observe_after_seconds": 30,
        "reason": "never control",
    }
""",
        tmp_path,
        version=1,
    )

    with pytest.raises(ValueError, match="bootstrap replay"):
        validate_strategy_replays(path)


def test_strategy_replays_require_proactive_bootstrap_control(
    tmp_path: Path,
) -> None:
    path = save_strategy_version(
        """
def decide(context):
    latest = context["history"][-1]
    rates = context["rates"]
    actions = []
    if latest["temperature_c"] >= 52 and rates["temperature_c_per_s"] > 0:
        actions.append({"switch": "cooling", "enabled": True})
    if latest["pressure_kpa"] >= 182 and rates["pressure_kpa_per_s"] > 0:
        actions.append({"switch": "relief", "enabled": True})
    if latest["temperature_c"] <= 35 and rates["temperature_c_per_s"] < 0:
        actions.append({"switch": "cooling", "enabled": False})
    if latest["pressure_kpa"] <= 165 and rates["pressure_kpa_per_s"] < 0:
        actions.append({"switch": "relief", "enabled": False})
    return {
        "observe": ["pressure", "temperature_rgb"],
        "actions": actions,
        "observe_after_seconds": 5,
        "reason": "waits for a measured trend",
    }
""",
        tmp_path,
        version=1,
    )

    with pytest.raises(ValueError, match="bootstrap replay"):
        validate_strategy_replays(path)
