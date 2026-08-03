#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SRC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SRC))

from week11_runtime.adaptive_policy import (  # noqa: E402
    run_strategy,
    save_strategy_version,
    validate_strategy_replays,
)
from week11_runtime.octos_protocol import (  # noqa: E402
    StrategyProposal,
    extract_octos_text,
    parse_octos_chat_response,
    parse_strategy_proposal,
)


ROOT = SRC
DEFAULT_OCTOS = Path(
    os.getenv("OCTOS_BIN")
    or shutil.which("octos")
    or Path.home() / ".local/bin/octos"
)
DEFAULT_OLLAMA = Path(
    os.getenv("OLLAMA_BIN")
    or shutil.which("ollama")
    or "ollama"
)
DEFAULT_MODEL = "qwen3-vl:8b-instruct"
DEFAULT_SUPERVISOR_MODEL = "qwen2.5-coder:7b"
DEFAULT_BASE_URL = "http://127.0.0.1:11434/v1"
NORMAL_RANGES = {
    "temperature_c": [30.0, 60.0],
    "pressure_kpa": [160.0, 200.0],
}
SOURCE_SKILL = SRC / "octos-skills" / "week11-process-supervision"
BASELINE_POLICY_SOURCE = """
def decide(context):
    latest = context["history"][-1]
    rates = context["rates"]
    switches = context["switch_state"]
    freshness = context["freshness_seconds"]
    actions = []

    if switches["cooling"]:
        if latest["temperature_c"] <= 35 and rates["temperature_c_per_s"] < 0:
            actions.append({"switch": "cooling", "enabled": False})
    elif latest["temperature_c"] >= 40 and rates["temperature_c_per_s"] >= 0:
        actions.append({"switch": "cooling", "enabled": True})

    if switches["relief"]:
        if latest["pressure_kpa"] <= 165 and rates["pressure_kpa_per_s"] < 0:
            actions.append({"switch": "relief", "enabled": False})
    elif latest["pressure_kpa"] >= 170 and rates["pressure_kpa_per_s"] >= 0:
        actions.append({"switch": "relief", "enabled": True})

    observe = []
    if (
        switches["cooling"]
        or latest["temperature_c"] >= 50
        or freshness["temperature"] >= 12
    ):
        observe.append("temperature_rgb")
    if (
        switches["relief"]
        or latest["pressure_kpa"] >= 180
        or freshness["pressure"] >= 12
    ):
        observe.append("pressure")
    if not observe:
        observe = ["pressure", "temperature_rgb"]

    if actions:
        observe_after_seconds = 3
    elif switches["cooling"] or switches["relief"]:
        observe_after_seconds = 4
    elif latest["temperature_c"] >= 50 or latest["pressure_kpa"] >= 180:
        observe_after_seconds = 5
    else:
        observe_after_seconds = 10

    return {
        "observe": observe,
        "actions": actions,
        "observe_after_seconds": observe_after_seconds,
        "reason": "adaptive control from values, trends, freshness, and state",
    }
""".strip()


class MissionError(RuntimeError):
    pass


class EventLog:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.path = output_dir / "mission-events.jsonl"

    def write(self, event: str, **data: Any) -> None:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            **data,
        }
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(json.dumps(record, ensure_ascii=False), flush=True)


class OctosAgent:
    def __init__(
        self,
        role: str,
        *,
        octos: Path,
        output_dir: Path,
        event_log: EventLog,
        profile: str = "coding-full",
        max_iterations: int = 12,
        config: Path | None = None,
        model: str = DEFAULT_MODEL,
    ) -> None:
        self.role = role
        self.octos = octos
        self.output_dir = output_dir
        self.event_log = event_log
        self.profile = profile
        self.max_iterations = max_iterations
        self.config = config
        self.model = model
        self.call_index = 0
        self.last_duration_seconds = 0.0

    def ask(
        self,
        prompt: str,
        *,
        expect_strategy: bool = False,
        retry_invalid_json: bool = True,
        execution_receipt: Path | None = None,
    ) -> dict | StrategyProposal:
        self.call_index += 1
        label = f"{self.role.lower()}-{self.call_index:02d}"
        command = [
            str(self.octos),
            "chat",
            "--cwd",
            str(ROOT),
            "--profile",
            self.profile,
            "--provider",
            "openai",
            "--model",
            self.model,
            "--base-url",
            DEFAULT_BASE_URL,
            "--api-type",
            "openai",
            "--effort",
            "medium",
            "--max-iterations",
            str(self.max_iterations),
            "--no-session-persistence",
            "--sandbox",
            "read-only",
            "--ask-for-approval",
            "never",
            "--json",
            "--message",
            prompt,
        ]
        if self.config is not None:
            command[2:2] = ["--config", str(self.config)]
        environment = os.environ.copy()
        environment.setdefault("OPENAI_API_KEY", "ollama")
        environment.setdefault("WEEK11_DORA_API", "http://127.0.0.1:8111")

        self.event_log.write(
            "agent_started",
            role=self.role,
            call=label,
            model=self.model,
        )
        started = time.monotonic()
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=360,
            check=False,
        )
        duration = round(time.monotonic() - started, 3)
        self.last_duration_seconds = duration
        (self.output_dir / f"{label}.stdout.json").write_text(
            completed.stdout,
            encoding="utf-8",
        )
        (self.output_dir / f"{label}.stderr.log").write_text(
            completed.stderr,
            encoding="utf-8",
        )
        if completed.returncode != 0:
            raise MissionError(
                f"{self.role} Octos call failed ({completed.returncode}); "
                f"see {label}.stderr.log"
            )

        if execution_receipt is not None and execution_receipt.is_file():
            try:
                result = json.loads(
                    execution_receipt.read_text(encoding="utf-8")
                )
            except (json.JSONDecodeError, OSError) as error:
                raise MissionError(
                    f"{self.role} execution receipt is invalid: {error}"
                ) from error
            self.event_log.write(
                "agent_completed",
                role=self.role,
                call=label,
                duration_seconds=duration,
                result_source="execution_receipt",
                result=result,
            )
            return result

        try:
            if expect_strategy:
                parsed: dict | StrategyProposal = parse_strategy_proposal(
                    extract_octos_text(completed.stdout)
                )
            else:
                parsed = parse_octos_chat_response(completed.stdout)
        except ValueError as error:
            if retry_invalid_json:
                self.event_log.write(
                    "agent_json_retry",
                    role=self.role,
                    call=label,
                    error=str(error),
                )
                return self.ask(
                    prompt
                    + "\nYour previous response did not match the required "
                    "JSON schema. Return only the requested JSON object.",
                    expect_strategy=expect_strategy,
                    retry_invalid_json=False,
                    execution_receipt=execution_receipt,
                )
            raise MissionError(
                f"{self.role} returned invalid JSON: {error}"
            ) from error

        serializable = (
            asdict(parsed)
            if isinstance(parsed, StrategyProposal)
            else parsed
        )
        self.event_log.write(
            "agent_completed",
            role=self.role,
            call=label,
            duration_seconds=duration,
            result=serializable,
        )
        return parsed


def unload_ollama_model(
    model: str,
    *,
    ollama: Path = DEFAULT_OLLAMA,
) -> bool:
    completed = subprocess.run(
        [str(ollama), "stop", model],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    return completed.returncode == 0


def sync_octos_skill(
    *,
    source_skill: Path = SOURCE_SKILL,
    workspace: Path = ROOT,
) -> Path:
    target = (
        workspace
        / ".octos"
        / "skills"
        / "week11-process-supervision"
    )
    target.mkdir(parents=True, exist_ok=True)
    for name in ("manifest.json", "main", "SKILL.md"):
        source = source_skill / name
        if not source.is_file():
            raise MissionError(f"Octos skill file is missing: {source}")
        shutil.copy2(source, target / name)
    return target


def observer_setup_prompt() -> str:
    return """
You are the Observer Agent in a running Dora/Webots process cell. The process
started with the simulation and is already heating and pressurizing.

Use only the installed process tools. Report your activity, call get_status,
and navigate the observer to station if it is not docked. Read pressure once,
read temperature once from the RGB camera and local VLM, then call get_status
again to obtain the current process simulation_time_s.

Return only:
{"role":"observer","location":"station","docked":true,
 "pressure_kpa":0.0,"pressure_observed_at_s":0.0,
 "temperature_c":0.0,"temperature_observed_at_s":0.0,
 "temperature_visible":true,"temperature_confidence":0.0,
 "temperature_image":"","model":""}
Copy values from tool results. Use the final process simulation_time_s as
temperature_observed_at_s.
""".strip()


def operator_setup_prompt() -> str:
    return """
You are the Operator Agent in a running Dora/Webots process cell. Use only the
installed process tools. Report your activity, call get_status, and navigate
the operator to station if it is not at the control position. Call get_status
again and return only:
{"role":"operator","location":"station","at_control":true,
 "cooling_on":false,"relief_open":false}
Copy the actual switch values from the nested process status.
""".strip()


def strategy_authoring_prompt(history: list[dict[str, Any]]) -> str:
    return f"""
You are the Supervisor Agent for a continuous two-robot process cell. Author a
small Python strategy that will be executed after every observation.

Goal:
- Keep temperature inside 30-60 C and pressure inside 160-200 kPa.
- Use timestamped history and measured rates to act before a trend leaves the
  safe range.
- The first context may contain only one observation, so both measured rates
  will be zero. Use the known positive nominal rates and preventive margins
  until a measured trend is available.
- Dynamically choose observation timing and whether pressure, RGB temperature,
  or both are needed.
- Reobserve after valve changes and decide later when to reverse them.
- Cooling and relief are the only switches. Cooling lowers temperature; relief
  lowers pressure. No heating or pressurizing action exists.
- The nominal unassisted rates are about +0.25 C/s and +0.32 kPa/s. With the
  matching valve active they are about -1.10 C/s and -3.18 kPa/s. Use these
  as initial evidence, then adapt from measured history.
- The process has no natural completion; the strategy must keep supervising.
- You may later keep this strategy unchanged or revise it from measured
  results.

The function signature is exactly:
def decide(context):

Context contains history, rates, switch_state, normal_ranges,
freshness_seconds, and completed_cycles. In particular, freshness_seconds is
the nested dictionary {{"temperature":0.0,"pressure":0.0}}; never compare that
dictionary itself with a number. Read current values with
latest = context["history"][-1]. There is no current top-level temperature_c
or pressure_kpa in context. Return:
{{"observe":["pressure","temperature_rgb"],
  "actions":[{{"switch":"cooling","enabled":true}}],
  "observe_after_seconds":8,
  "reason":"evidence-based explanation"}}

Code restrictions:
- Define only decide(context); do not import anything.
- Use dictionary/list indexing, arithmetic, comparisons, if/elif/else, local
  variables, reversed, list.append, and safe calls abs, min, max, round, len,
  or dict.get.
- Do not use files, shell, network, other attributes, while loops, classes,
  exceptions, dynamic evaluation, or private names.
- The returned observe list must never be empty. If selective conditions add
  nothing, fall back to both pressure and temperature_rgb in executable code.
  Observation timing may be any integer from 1 to 120 seconds; choose it from
  current evidence rather than a fixed cadence.
- Do not repeat a valve state already present in context["switch_state"].
- Evaluate temperature and pressure with independent if statements so both
  controls can change in one decision when both trends require it.
- Use context["rates"]["temperature_c_per_s"] and
  context["rates"]["pressure_kpa_per_s"] as per-second trend evidence.

Initial timestamped history:
{json.dumps(history, separators=(",", ":"))}

Start from this replay-verified baseline. Preserve its context access, list
schemas, independent controls, and upper/lower safeguards. You may adjust
numeric margins, sensor selection, and timing when the measured evidence
supports it. Return it unchanged if there is not enough evidence to improve it:
{BASELINE_POLICY_SOURCE}

Return one JSON object only:
{{"strategy_source":"complete Python source","reason":"design rationale"}}
""".strip()


def observation_prompt(
    sensors: list[str],
    *,
    wait_seconds: int,
) -> str:
    instructions: list[str] = []
    output_fields: list[str] = []
    if "pressure" in sensors:
        instructions.append("call read_pressure exactly once")
        output_fields.extend(
            ['"pressure_kpa":0.0', '"pressure_observed_at_s":0.0']
        )
    if "temperature_rgb" in sensors:
        instructions.append("call read_temperature exactly once")
        output_fields.extend(
            [
                '"temperature_c":0.0',
                '"temperature_observed_at_s":0.0',
                '"temperature_visible":true',
                '"temperature_confidence":0.0',
                '"temperature_image":""',
                '"model":""',
            ]
        )
    instructions.append(
        "call get_status exactly once afterward, copy cooling_on and "
        "relief_open, and use process simulation_time_s as "
        "temperature_observed_at_s when temperature was requested"
    )
    output_fields.extend(['"cooling_on":false', '"relief_open":false'])
    action_text = ", then ".join(instructions)
    fields = ",".join(output_fields)
    return f"""
You are the Observer Agent continuing a process-supervision mission. First
call wait_seconds with seconds={wait_seconds}. Report your activity, then
{action_text}. Use only the installed process tools.

Return one JSON object only:
{{"role":"observer","location":"station","docked":true,{fields}}}
Include the requested sensor fields plus cooling_on and relief_open. Copy
every value from tool results.
""".strip()


def operator_actions_prompt(
    action_id: str,
    actions: list[dict[str, Any]],
) -> str:
    payload = {"action_id": action_id, "actions": actions}
    return f"""
You are the Operator Agent at the control station. The active Octos strategy
selected these immediate valve state changes:
{json.dumps(payload, separators=(",", ":"))}

Report your activity, then call apply_switch_actions exactly once with this
action_id and actions. Preserve both exactly. Do not add a timer or future
shutdown. Return only the JSON object produced by apply_switch_actions.
""".strip()


def strategy_review_prompt(
    current_source: str,
    context: dict[str, Any],
) -> str:
    return f"""
You are the Supervisor Agent reviewing an adaptive process strategy after a
complete valve-control cycle. Based on observed rates, timing, sensor
freshness, and whether the cycle stayed inside 30-60 C and 160-200 kPa,
keep it unchanged or revise it. Preserve the same restricted decide(context)
interface and coding rules.

Current strategy:
{current_source}

Current context:
{json.dumps(context, separators=(",", ":"))}

Return one JSON object only:
{{"strategy_source":"complete Python source","reason":"review rationale"}}
""".strip()


def should_review_strategy(
    completed_cycles: int,
    *,
    interval: int = 3,
) -> bool:
    if interval < 1:
        raise ValueError("interval must be positive")
    return completed_cycles > 0 and completed_cycles % interval == 0


def strategy_correction_prompt(
    base_prompt: str,
    source: str,
    error: str,
) -> str:
    repair_hint = ""
    if "freshness_seconds" in error and "dict" in error:
        repair_hint = """
Change the executable source. freshness_seconds is a dictionary. Delete any
comparison between freshness_seconds itself and a number. If staleness is
needed, compute:
stale_seconds = max(
    freshness_seconds["temperature"],
    freshness_seconds["pressure"],
)
and compare stale_seconds with a number.
""".strip()
    elif "observe must be a non-empty sensor list" in error:
        repair_hint = """
Change the executable source, not only the reason text. Immediately before
the return, add this equivalent fallback using the source's observation list:
if not observe_list:
    observe_list = ["pressure", "temperature_rgb"]
Then return observe_list as the observe field.
""".strip()
    elif "actions must be an array" in error:
        repair_hint = """
Change the executable source. Initialize actions = [] and only add action
objects with actions.append({"switch": "cooling", "enabled": True}) or the
equivalent relief/False forms. Never assign {} to actions.
""".strip()
    elif "bootstrap replay" in error:
        repair_hint = """
Change the executable source so the first one-sample context is proactive.
Measured rates are zero until a second sample exists, but the known nominal
process rates are positive. Use independent conditions equivalent to:
if latest["temperature_c"] >= 40 and rates["temperature_c_per_s"] >= 0 and not switches["cooling"]:
    actions.append({"switch": "cooling", "enabled": True})
if latest["pressure_kpa"] >= 170 and rates["pressure_kpa_per_s"] >= 0 and not switches["relief"]:
    actions.append({"switch": "relief", "enabled": True})
Both actions must be returned when both values are near their maxima.
""".strip()
    elif "upper-range replay" in error:
        repair_hint = """
Change the executable source using this access pattern:
latest = context["history"][-1]
rates = context["rates"]
switches = context["switch_state"]
Use independent if statements equivalent to:
if latest["temperature_c"] >= 55 and rates["temperature_c_per_s"] > 0 and not switches["cooling"]:
    actions.append({"switch": "cooling", "enabled": True})
if latest["pressure_kpa"] >= 190 and rates["pressure_kpa_per_s"] > 0 and not switches["relief"]:
    actions.append({"switch": "relief", "enabled": True})
Do not read temperature_c or pressure_kpa directly from context. Both actions
must be returned when both conditions are true.
""".strip()
    elif "lower-range replay" in error:
        repair_hint = """
Change the executable source using this access pattern:
latest = context["history"][-1]
rates = context["rates"]
switches = context["switch_state"]
Use independent if statements equivalent to:
if latest["temperature_c"] <= 35 and rates["temperature_c_per_s"] < 0 and switches["cooling"]:
    actions.append({"switch": "cooling", "enabled": False})
if latest["pressure_kpa"] <= 165 and rates["pressure_kpa_per_s"] < 0 and switches["relief"]:
    actions.append({"switch": "relief", "enabled": False})
Do not read temperature_c or pressure_kpa directly from context. Both actions
must be returned when both conditions are true.
""".strip()
    return f"""
{base_prompt}

The previous strategy was rejected before activation.
Validation error:
{error}

Rejected source:
{source}

Required code-level repair:
{repair_hint or "Change the executable source to satisfy the validator error."}

Correct the source while preserving adaptive timing and trend-based decisions.
Cooling and relief are the only switches. The bootstrap replay must act near
the maxima even before a measured rate exists. The upper-range replay must
enable both controls when both values are rising near their maxima. The
lower-range replay must disable both controls when both values are falling
near their minima. Do not return heating or pressurizing actions.

Return one corrected JSON object only:
{{"strategy_source":"complete Python source","reason":"correction rationale"}}
""".strip()


def prepare_agents_concurrently(
    observer: OctosAgent,
    operator: OctosAgent,
) -> tuple[dict[str, Any], dict[str, Any]]:
    with ThreadPoolExecutor(max_workers=2) as executor:
        observer_future = executor.submit(
            observer.ask,
            observer_setup_prompt(),
        )
        operator_future = executor.submit(
            operator.ask,
            operator_setup_prompt(),
        )
        observation = observer_future.result()
        operator_state = operator_future.result()
    if not isinstance(observation, dict) or not isinstance(
        operator_state,
        dict,
    ):
        raise MissionError("agent preparation returned an invalid result")
    return observation, operator_state


OBSERVATION_FIELDS = (
    "temperature_c",
    "temperature_observed_at_s",
    "pressure_kpa",
    "pressure_observed_at_s",
)


def merge_observation(
    previous: dict[str, Any],
    partial: dict[str, Any],
) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for field in OBSERVATION_FIELDS:
        if field in partial and partial[field] is not None:
            merged[field] = partial[field]
        elif field in previous:
            merged[field] = previous[field]
        else:
            raise ValueError(f"observation is missing {field}")
    return merged


def reconcile_switch_state(
    current: dict[str, bool],
    partial: dict[str, Any],
) -> dict[str, bool]:
    reconciled = dict(current)
    observed_fields = {
        "cooling": "cooling_on",
        "relief": "relief_open",
    }
    for switch, field in observed_fields.items():
        if field not in partial:
            continue
        observed = partial[field]
        if not isinstance(observed, bool):
            raise ValueError(f"{field} must be a boolean")
        reconciled[switch] = observed
    return reconciled


def shutdown_switch_actions(
    switch_state: dict[str, bool],
) -> list[dict[str, Any]]:
    return [
        {"switch": switch, "enabled": False}
        for switch in ("cooling", "relief")
        if switch_state[switch]
    ]


def _rate(
    history: list[dict[str, Any]],
    value_field: str,
    time_field: str,
) -> float:
    if len(history) < 2:
        return 0.0
    current = history[-1]
    previous = history[-2]
    elapsed = float(current[time_field]) - float(previous[time_field])
    if elapsed <= 0.0:
        return 0.0
    return round(
        (float(current[value_field]) - float(previous[value_field]))
        / elapsed,
        6,
    )


def build_policy_context(
    history: list[dict[str, Any]],
    switch_state: dict[str, bool],
    *,
    completed_cycles: int,
) -> dict[str, Any]:
    latest = history[-1]
    latest_time = max(
        float(latest["temperature_observed_at_s"]),
        float(latest["pressure_observed_at_s"]),
    )
    return {
        "history": history[-12:],
        "rates": {
            "temperature_c_per_s": _rate(
                history,
                "temperature_c",
                "temperature_observed_at_s",
            ),
            "pressure_kpa_per_s": _rate(
                history,
                "pressure_kpa",
                "pressure_observed_at_s",
            ),
        },
        "freshness_seconds": {
            "temperature": round(
                latest_time - float(latest["temperature_observed_at_s"]),
                3,
            ),
            "pressure": round(
                latest_time - float(latest["pressure_observed_at_s"]),
                3,
            ),
        },
        "switch_state": dict(switch_state),
        "normal_ranges": NORMAL_RANGES,
        "completed_cycles": completed_cycles,
    }


def _initial_observation(raw: dict[str, Any]) -> dict[str, Any]:
    result = merge_observation({}, raw)
    if not bool(raw.get("docked")):
        raise MissionError("Observer is not docked after preparation")
    if not bool(raw.get("temperature_visible", True)):
        raise MissionError("Temperature display was not visible")
    return result


def _inside_normal_ranges(observation: dict[str, Any]) -> bool:
    return (
        30.0 <= float(observation["temperature_c"]) <= 60.0
        and 160.0 <= float(observation["pressure_kpa"]) <= 200.0
    )


def _save_and_probe_strategy(
    proposal: StrategyProposal,
    *,
    policy_dir: Path,
    version: int,
    context: dict[str, Any],
) -> Path:
    path = save_strategy_version(
        proposal.source,
        policy_dir,
        version=version,
    )
    run_strategy(path, context)
    validate_strategy_replays(path)
    return path


def activate_supervisor_strategy(
    supervisor,
    *,
    initial_prompt: str,
    policy_dir: Path,
    context: dict[str, Any],
    event_log: EventLog,
    version: int,
    max_attempts: int = 4,
    fallback_source: str = BASELINE_POLICY_SOURCE,
) -> tuple[Path, StrategyProposal]:
    prompt = initial_prompt
    for attempt in range(1, max_attempts + 1):
        proposal = supervisor.ask(prompt, expect_strategy=True)
        if not isinstance(proposal, StrategyProposal):
            raise MissionError("Supervisor did not return a strategy proposal")
        try:
            path = _save_and_probe_strategy(
                proposal,
                policy_dir=policy_dir,
                version=version,
                context=context,
            )
        except (OSError, RuntimeError, ValueError) as error:
            event_log.write(
                "strategy_rejected",
                version=version,
                attempt=attempt,
                error=str(error),
                reason=proposal.reason,
            )
            if attempt == max_attempts:
                break
            prompt = strategy_correction_prompt(
                initial_prompt,
                proposal.source,
                str(error),
            )
            continue
        return path, proposal
    fallback = StrategyProposal(
        source=fallback_source,
        reason="activated replay-verified fallback after candidate rejection",
    )
    path = _save_and_probe_strategy(
        fallback,
        policy_dir=policy_dir,
        version=version,
        context=context,
    )
    event_log.write(
        "strategy_fallback_activated",
        version=version,
        path=str(path),
        reason=fallback.reason,
    )
    return path, fallback


def run_mission(args: argparse.Namespace) -> Path:
    run_name = args.run_name or datetime.now().strftime(
        "adaptive-%Y%m%d-%H%M%S"
    )
    output_dir = Path(args.output_dir) / run_name
    event_log = EventLog(output_dir)
    installed_skill = sync_octos_skill()
    event_log.write(
        "octos_skill_synced",
        source=str(SOURCE_SKILL),
        target=str(installed_skill),
    )
    observer = OctosAgent(
        "Observer",
        octos=Path(args.octos),
        output_dir=output_dir,
        event_log=event_log,
        model=args.vision_model,
    )
    operator = OctosAgent(
        "Operator",
        octos=Path(args.octos),
        output_dir=output_dir,
        event_log=event_log,
        model=args.vision_model,
    )
    supervisor = OctosAgent(
        "Supervisor",
        octos=Path(args.octos),
        output_dir=output_dir,
        event_log=event_log,
        profile="coding",
        max_iterations=1,
        config=SRC / "config" / "octos-supervisor.json",
        model=args.supervisor_model,
    )

    running = True

    def stop(*_args) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    event_log.write(
        "mission_started",
        run_name=run_name,
        mode="continuous_adaptive",
    )
    setup_observation, operator_state = prepare_agents_concurrently(
        observer,
        operator,
    )
    unload_ollama_model(args.vision_model, ollama=Path(args.ollama))
    event_log.write(
        "model_unloaded",
        model=args.vision_model,
        next_role="Supervisor",
    )
    history = [_initial_observation(setup_observation)]
    switch_state = {
        "cooling": bool(operator_state.get("cooling_on")),
        "relief": bool(operator_state.get("relief_open")),
    }
    completed_cycles = 0
    active_cycle = any(switch_state.values())
    context = build_policy_context(
        history,
        switch_state,
        completed_cycles=completed_cycles,
    )
    policy_dir = output_dir / "generated-policy"
    policy_version = 1
    try:
        policy_path, proposal = activate_supervisor_strategy(
            supervisor,
            initial_prompt=strategy_authoring_prompt(history),
            policy_dir=policy_dir,
            context=context,
            event_log=event_log,
            version=policy_version,
        )
    finally:
        unload_ollama_model(
            args.supervisor_model,
            ollama=Path(args.ollama),
        )
    event_log.write(
        "strategy_activated",
        version=policy_version,
        path=str(policy_path),
        reason=proposal.reason,
    )

    started = time.monotonic()
    decision_index = 0
    while running:
        if args.max_duration > 0 and time.monotonic() - started >= args.max_duration:
            break
        context = build_policy_context(
            history,
            switch_state,
            completed_cycles=completed_cycles,
        )
        decision = run_strategy(policy_path, context)
        decision_index += 1
        event_log.write(
            "strategy_decision",
            index=decision_index,
            policy_version=policy_version,
            context=context,
            decision=decision,
        )

        actions = [
            action
            for action in decision["actions"]
            if switch_state[action["switch"]] is not action["enabled"]
        ]
        if actions:
            action_id = f"{run_name}-action-{decision_index:03d}"
            receipt = (
                SRC
                / "outputs"
                / "switch-action-receipts"
                / f"{action_id}.json"
            )
            result = operator.ask(
                operator_actions_prompt(action_id, actions),
                execution_receipt=receipt,
            )
            if not isinstance(result, dict) or not result.get("all_succeeded"):
                raise MissionError("Operator reported a failed switch action")
            for event in result["events"]:
                switch_state[event["switch"]] = bool(event["enabled"])
            if any(switch_state.values()):
                active_cycle = True
            event_log.write(
                "switch_actions_completed",
                decision_index=decision_index,
                result=result,
                switch_state=switch_state,
            )

        partial = observer.ask(
            observation_prompt(
                decision["observe"],
                wait_seconds=decision["observe_after_seconds"],
            )
        )
        if not isinstance(partial, dict):
            raise MissionError("Observer returned an invalid observation")
        observation = merge_observation(history[-1], partial)
        previous_switch_state = switch_state
        switch_state = reconcile_switch_state(switch_state, partial)
        if switch_state != previous_switch_state:
            event_log.write(
                "switch_state_reconciled",
                decision_index=decision_index,
                previous=previous_switch_state,
                observed=switch_state,
            )
        if any(switch_state.values()):
            active_cycle = True
        history.append(observation)
        event_log.write(
            "observation_completed",
            decision_index=decision_index,
            requested_sensors=decision["observe"],
            observation=observation,
            switch_state=switch_state,
        )

        cycle_completed_now = (
            active_cycle
            and not any(switch_state.values())
            and _inside_normal_ranges(observation)
        )
        if cycle_completed_now:
            completed_cycles += 1
            active_cycle = False
            event_log.write(
                "control_cycle_completed",
                completed_cycles=completed_cycles,
                observation=observation,
            )
            if not should_review_strategy(completed_cycles):
                continue
            review_context = build_policy_context(
                history,
                switch_state,
                completed_cycles=completed_cycles,
            )
            review_prompt = strategy_review_prompt(
                policy_path.read_text(encoding="utf-8"),
                review_context,
            )
            unload_ollama_model(
                args.vision_model,
                ollama=Path(args.ollama),
            )
            event_log.write(
                "model_unloaded",
                model=args.vision_model,
                next_role="Supervisor",
            )
            try:
                candidate_path, reviewed = activate_supervisor_strategy(
                    supervisor,
                    initial_prompt=review_prompt,
                    policy_dir=policy_dir,
                    context=review_context,
                event_log=event_log,
                version=policy_version + 1,
                fallback_source=policy_path.read_text(encoding="utf-8"),
            )
            finally:
                unload_ollama_model(
                    args.supervisor_model,
                    ollama=Path(args.ollama),
                )
            if reviewed.source != policy_path.read_text(encoding="utf-8"):
                policy_version += 1
                policy_path = candidate_path
                event_log.write(
                    "strategy_revised",
                    version=policy_version,
                    path=str(policy_path),
                    reason=reviewed.reason,
                )
            else:
                candidate_path.unlink(missing_ok=True)
                event_log.write(
                    "strategy_retained",
                    version=policy_version,
                    reason=reviewed.reason,
                )

    shutdown_actions = shutdown_switch_actions(switch_state)
    if shutdown_actions:
        action_id = f"{run_name}-shutdown-{decision_index:03d}"
        receipt = (
            SRC
            / "outputs"
            / "switch-action-receipts"
            / f"{action_id}.json"
        )
        shutdown_result = operator.ask(
            operator_actions_prompt(action_id, shutdown_actions),
            execution_receipt=receipt,
        )
        if (
            not isinstance(shutdown_result, dict)
            or not shutdown_result.get("all_succeeded")
        ):
            raise MissionError("Operator reported a failed shutdown action")
        for event in shutdown_result["events"]:
            switch_state[event["switch"]] = bool(event["enabled"])
        event_log.write(
            "shutdown_switch_actions_completed",
            result=shutdown_result,
            switch_state=switch_state,
        )

    event_log.write(
        "mission_stopped",
        decisions=decision_index,
        completed_cycles=completed_cycles,
        final_observation=history[-1],
        switch_state=switch_state,
    )
    return output_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--octos", default=str(DEFAULT_OCTOS))
    parser.add_argument("--ollama", default=str(DEFAULT_OLLAMA))
    parser.add_argument("--vision-model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--supervisor-model",
        default=DEFAULT_SUPERVISOR_MODEL,
    )
    parser.add_argument(
        "--output-dir",
        default=str(SRC / "outputs" / "octos-runs"),
    )
    parser.add_argument("--run-name")
    parser.add_argument("--max-duration", type=float, default=0.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        output_dir = run_mission(args)
    except (MissionError, OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"ERROR: {error}", file=sys.stderr, flush=True)
        raise SystemExit(1)
    print(json.dumps({"output_dir": str(output_dir)}), flush=True)


if __name__ == "__main__":
    main()
