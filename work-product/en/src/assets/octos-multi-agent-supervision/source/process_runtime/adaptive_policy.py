from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


VALID_SENSORS = {"pressure", "temperature_rgb"}
VALID_SWITCHES = {"cooling", "relief"}
SAFE_CALLS = {"abs", "len", "max", "min", "reversed", "round"}
SAFE_ATTRIBUTES = {"append", "get"}
REJECTED_NODES = (
    ast.AsyncFunctionDef,
    ast.Await,
    ast.ClassDef,
    ast.Delete,
    ast.Global,
    ast.Import,
    ast.ImportFrom,
    ast.Lambda,
    ast.Nonlocal,
    ast.Raise,
    ast.Try,
    ast.While,
    ast.With,
    ast.Yield,
    ast.YieldFrom,
)


def validate_strategy_source(source: str) -> None:
    if not isinstance(source, str) or not source.strip():
        raise ValueError("strategy source must be a non-empty string")
    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        raise ValueError(f"strategy source is invalid Python: {error}") from error

    functions = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    if len(functions) != 1 or functions[0].name != "decide":
        raise ValueError("strategy must define exactly one decide function")
    if len(tree.body) != 1:
        raise ValueError("strategy may only contain the decide function")

    function = functions[0]
    if function.decorator_list:
        raise ValueError("strategy decide function cannot use decorators")
    if (
        len(function.args.args) != 1
        or function.args.args[0].arg != "context"
        or function.args.vararg is not None
        or function.args.kwarg is not None
    ):
        raise ValueError("strategy decide function must accept only context")

    for node in ast.walk(tree):
        if isinstance(node, REJECTED_NODES):
            raise ValueError(
                f"strategy syntax is not allowed: {type(node).__name__}"
            )
        if isinstance(node, ast.Name) and node.id.startswith("__"):
            raise ValueError("strategy cannot access private runtime names")
        if isinstance(node, ast.Attribute):
            if node.attr not in SAFE_ATTRIBUTES:
                raise ValueError(
                    f"strategy attribute is not allowed: {node.attr}"
                )
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id not in SAFE_CALLS:
                    raise ValueError(
                        f"strategy call is not allowed: {node.func.id}"
                    )
            elif not (
                isinstance(node.func, ast.Attribute)
                and node.func.attr in SAFE_ATTRIBUTES
            ):
                raise ValueError("strategy call target is not allowed")


def save_strategy_version(
    source: str,
    directory: Path,
    *,
    version: int,
) -> Path:
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise ValueError("strategy version must be a positive integer")
    validate_strategy_source(source)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"strategy-v{version:03d}.py"
    temporary_path = path.with_suffix(".py.tmp")
    temporary_path.write_text(source, encoding="utf-8")
    temporary_path.replace(path)
    return path


def _validate_observe(raw: object) -> list[str]:
    if not isinstance(raw, list) or not raw:
        raise ValueError("observe must be a non-empty sensor list")
    if (
        any(not isinstance(sensor, str) or sensor not in VALID_SENSORS for sensor in raw)
        or len(set(raw)) != len(raw)
    ):
        raise ValueError("sensor must be pressure or temperature_rgb without duplicates")
    return raw


def _validate_actions(raw: object) -> list[dict[str, Any]]:
    if not isinstance(raw, list) or len(raw) > 2:
        raise ValueError("actions must be an array with at most two items")
    seen: set[str] = set()
    for action in raw:
        if not isinstance(action, dict):
            raise ValueError("each switch action must be an object")
        switch = action.get("switch")
        enabled = action.get("enabled")
        if switch not in VALID_SWITCHES:
            raise ValueError("switch must be cooling or relief")
        if switch in seen:
            raise ValueError(f"{switch} appears more than once")
        if not isinstance(enabled, bool):
            raise ValueError("switch enabled must be a boolean")
        seen.add(switch)
    return raw


def validate_strategy_decision(
    decision: object,
    context: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(decision, dict):
        raise ValueError("strategy decision must be an object")
    observe = _validate_observe(decision.get("observe"))
    actions = _validate_actions(decision.get("actions"))
    interval = decision.get("observe_after_seconds")
    if (
        not isinstance(interval, int)
        or isinstance(interval, bool)
        or not 1 <= interval <= 120
    ):
        raise ValueError("observe_after_seconds must be between 1 and 120")
    reason = decision.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("reason must be a non-empty string")

    history = context.get("history")
    if not isinstance(history, list) or not history:
        raise ValueError("strategy context requires observation history")
    latest = history[-1]
    ranges = context.get("normal_ranges")
    if not isinstance(latest, dict) or not isinstance(ranges, dict):
        raise ValueError("strategy context is malformed")
    temperature_min = float(ranges["temperature_c"][0])
    pressure_min = float(ranges["pressure_kpa"][0])
    for action in actions:
        if (
            action["switch"] == "cooling"
            and action["enabled"]
            and float(latest["temperature_c"]) <= temperature_min
        ):
            raise ValueError("cooling cannot be enabled at its lower bound")
        if (
            action["switch"] == "relief"
            and action["enabled"]
            and float(latest["pressure_kpa"]) <= pressure_min
        ):
            raise ValueError("relief cannot be enabled at its lower bound")

    return {
        "observe": list(observe),
        "actions": [dict(action) for action in actions],
        "observe_after_seconds": interval,
        "reason": reason.strip(),
    }


def run_strategy(
    path: Path,
    context: dict[str, Any],
    *,
    timeout_seconds: float = 2.0,
) -> dict[str, Any]:
    source = path.read_text(encoding="utf-8")
    validate_strategy_source(source)
    helper = Path(__file__).resolve().parents[1] / "tools" / "run_generated_policy.py"
    environment = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONIOENCODING": "utf-8",
    }
    if os.name == "nt":
        for name in ("SYSTEMROOT", "WINDIR"):
            if value := os.environ.get(name):
                environment[name] = value
    try:
        completed = subprocess.run(
            [sys.executable, "-I", str(helper), str(path)],
            input=json.dumps(context),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
            env=environment,
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError("strategy execution timed out") from error
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"strategy execution failed: {detail}")
    try:
        decision = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError("strategy output is not valid JSON") from error
    return validate_strategy_decision(decision, context)


def _replay_context(
    previous: dict[str, float],
    latest: dict[str, float],
    switch_state: dict[str, bool],
    rates: dict[str, float],
) -> dict[str, Any]:
    return {
        "history": [previous, latest],
        "rates": rates,
        "freshness_seconds": {"temperature": 0.0, "pressure": 0.0},
        "switch_state": switch_state,
        "normal_ranges": {
            "temperature_c": [30.0, 60.0],
            "pressure_kpa": [160.0, 200.0],
        },
        "completed_cycles": 1,
    }


def validate_strategy_replays(path: Path) -> None:
    bootstrap_context = {
        "history": [
            {
                "temperature_c": 40.0,
                "temperature_observed_at_s": 60.0,
                "pressure_kpa": 170.0,
                "pressure_observed_at_s": 48.0,
            }
        ],
        "rates": {
            "temperature_c_per_s": 0.0,
            "pressure_kpa_per_s": 0.0,
        },
        "freshness_seconds": {"temperature": 0.0, "pressure": 12.0},
        "switch_state": {"cooling": False, "relief": False},
        "normal_ranges": {
            "temperature_c": [30.0, 60.0],
            "pressure_kpa": [160.0, 200.0],
        },
        "completed_cycles": 0,
    }
    bootstrap = run_strategy(path, bootstrap_context)
    bootstrap_actions = {
        (action["switch"], action["enabled"])
        for action in bootstrap["actions"]
    }
    required_bootstrap = {("cooling", True), ("relief", True)}
    if not required_bootstrap.issubset(bootstrap_actions):
        raise ValueError(
            "bootstrap replay must enable cooling and relief near the normal "
            "maxima when measured rates are not available yet"
        )

    upper_context = _replay_context(
        {
            "temperature_c": 57.0,
            "temperature_observed_at_s": 10.0,
            "pressure_kpa": 192.0,
            "pressure_observed_at_s": 10.0,
        },
        {
            "temperature_c": 59.0,
            "temperature_observed_at_s": 20.0,
            "pressure_kpa": 198.0,
            "pressure_observed_at_s": 20.0,
        },
        {"cooling": False, "relief": False},
        {"temperature_c_per_s": 0.25, "pressure_kpa_per_s": 0.32},
    )
    upper = run_strategy(path, upper_context)
    upper_actions = {
        (action["switch"], action["enabled"])
        for action in upper["actions"]
    }
    required_upper = {("cooling", True), ("relief", True)}
    if not required_upper.issubset(upper_actions):
        raise ValueError(
            "upper-range replay must enable cooling and relief while both "
            "values are rising near their normal maxima"
        )

    lower_context = _replay_context(
        {
            "temperature_c": 35.0,
            "temperature_observed_at_s": 10.0,
            "pressure_kpa": 170.0,
            "pressure_observed_at_s": 10.0,
        },
        {
            "temperature_c": 31.0,
            "temperature_observed_at_s": 20.0,
            "pressure_kpa": 162.0,
            "pressure_observed_at_s": 20.0,
        },
        {"cooling": True, "relief": True},
        {"temperature_c_per_s": -1.10, "pressure_kpa_per_s": -3.18},
    )
    lower = run_strategy(path, lower_context)
    lower_actions = {
        (action["switch"], action["enabled"])
        for action in lower["actions"]
    }
    required_lower = {("cooling", False), ("relief", False)}
    if not required_lower.issubset(lower_actions):
        raise ValueError(
            "lower-range replay must disable cooling and relief while both "
            "values are falling near their normal minima"
        )
