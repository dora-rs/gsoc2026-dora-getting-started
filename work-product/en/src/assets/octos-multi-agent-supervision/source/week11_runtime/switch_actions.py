from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any


SetSwitch = Callable[[str, bool], dict[str, Any]]
ACTION_ID_PATTERN = re.compile(r"[A-Za-z0-9._-]{1,80}")
VALID_SWITCHES = {"cooling", "relief"}


def _validate_actions(
    actions: list[dict[str, Any]],
    current_state: Mapping[str, bool],
) -> None:
    if not isinstance(actions, list) or not 1 <= len(actions) <= 2:
        raise ValueError("switch actions must contain one or two items")
    seen: set[str] = set()
    for action in actions:
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


def _require_success(result: dict[str, Any]) -> None:
    if result.get("status") == "succeeded" or result.get("success") is True:
        return
    raise RuntimeError(f"switch command failed: {result}")


def execute_switch_actions_once(
    action_id: str,
    actions: list[dict[str, Any]],
    *,
    current_state: Mapping[str, bool],
    receipt_dir: Path,
    set_switch: SetSwitch,
) -> dict[str, Any]:
    if (
        not isinstance(action_id, str)
        or not ACTION_ID_PATTERN.fullmatch(action_id)
    ):
        raise ValueError(
            "action_id must contain only letters, digits, dot, dash, or underscore"
        )
    receipt_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = receipt_dir / f"{action_id}.json"
    if receipt_path.is_file():
        return json.loads(receipt_path.read_text(encoding="utf-8"))

    _validate_actions(actions, current_state)
    events: list[dict[str, Any]] = []
    for action in actions:
        switch = str(action["switch"])
        enabled = bool(action["enabled"])
        if bool(current_state.get(switch)) is enabled:
            events.append(
                {
                    "switch": switch,
                    "enabled": enabled,
                    "status": "already_satisfied",
                }
            )
            continue
        result = set_switch(switch, enabled)
        _require_success(result)
        events.append(
            {
                "switch": switch,
                "enabled": enabled,
                "status": "succeeded",
            }
        )

    receipt = {
        "action_id": action_id,
        "events": events,
        "all_succeeded": True,
    }
    temporary_path = receipt_path.with_suffix(".json.tmp")
    temporary_path.write_text(
        json.dumps(receipt, separators=(",", ":")),
        encoding="utf-8",
    )
    temporary_path.replace(receipt_path)
    return receipt
