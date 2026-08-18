from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any


SetSwitch = Callable[[str, bool], dict[str, Any]]
Sleep = Callable[[float], None]
Monotonic = Callable[[], float]
PLAN_ID_PATTERN = re.compile(r"[A-Za-z0-9._-]{1,80}")


def _validate_plans(plans: list[dict[str, Any]]) -> None:
    if not 1 <= len(plans) <= 2:
        raise ValueError("control plan must contain one or two switches")
    seen: set[str] = set()
    for plan in plans:
        switch = plan.get("switch")
        if switch not in {"cooling", "relief"}:
            raise ValueError("switch must be cooling or relief")
        if switch in seen:
            raise ValueError(f"{switch} appears more than once")
        seen.add(switch)
        hold = plan.get("disable_after_seconds")
        if (
            not isinstance(hold, int)
            or isinstance(hold, bool)
            or not 2 <= hold <= 30
        ):
            raise ValueError(
                "disable_after_seconds must be between 2 and 30"
            )


def _require_success(result: dict[str, Any]) -> None:
    if result.get("status") == "succeeded" or result.get("success") is True:
        return
    raise RuntimeError(f"switch command failed: {result}")


def execute_control_plan(
    plans: list[dict[str, Any]],
    *,
    set_switch: SetSwitch,
    sleep: Sleep,
    monotonic: Monotonic,
) -> dict[str, Any]:
    _validate_plans(plans)
    started = monotonic()
    events: list[dict[str, Any]] = []
    shutdowns: list[tuple[float, str]] = []

    for plan in plans:
        switch = str(plan["switch"])
        result = set_switch(switch, True)
        _require_success(result)
        completed = monotonic()
        events.append(
            {
                "switch": switch,
                "enabled": True,
                "completed_at_seconds": round(completed - started, 3),
            }
        )
        shutdowns.append(
            (
                completed + int(plan["disable_after_seconds"]),
                switch,
            )
        )

    for due_at, switch in sorted(shutdowns):
        remaining = due_at - monotonic()
        if remaining > 0.0:
            sleep(remaining)
        result = set_switch(switch, False)
        _require_success(result)
        events.append(
            {
                "switch": switch,
                "enabled": False,
                "completed_at_seconds": round(
                    monotonic() - started, 3
                ),
            }
        )

    return {
        "events": events,
        "all_succeeded": True,
        "elapsed_seconds": round(monotonic() - started, 3),
    }


def execute_control_plan_once(
    plan_id: str,
    plans: list[dict[str, Any]],
    *,
    receipt_dir: Path,
    set_switch: SetSwitch,
    sleep: Sleep,
    monotonic: Monotonic,
) -> dict[str, Any]:
    if not isinstance(plan_id, str) or not PLAN_ID_PATTERN.fullmatch(plan_id):
        raise ValueError("plan_id must contain only letters, digits, dot, dash, or underscore")
    receipt_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = receipt_dir / f"{plan_id}.json"
    if receipt_path.is_file():
        return json.loads(receipt_path.read_text(encoding="utf-8"))

    result = {
        "plan_id": plan_id,
        **execute_control_plan(
            plans,
            set_switch=set_switch,
            sleep=sleep,
            monotonic=monotonic,
        ),
    }
    temporary_path = receipt_path.with_suffix(".json.tmp")
    temporary_path.write_text(
        json.dumps(result, separators=(",", ":")),
        encoding="utf-8",
    )
    temporary_path.replace(receipt_path)
    return result
