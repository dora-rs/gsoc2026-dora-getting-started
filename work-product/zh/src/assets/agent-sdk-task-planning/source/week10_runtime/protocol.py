from __future__ import annotations

from datetime import datetime, timezone

from robot_api.contracts import RobotState


def parse_controller_state(payload: dict) -> RobotState:
    values = dict(payload)
    timestamp = values.pop("captured_at_unix_s")
    values.pop("switch_state", None)
    values["captured_at"] = datetime.fromtimestamp(
        timestamp, tz=timezone.utc
    )
    return RobotState.model_validate(values)


def action_result(
    request_id: str,
    *,
    status: str,
    message: str,
    retryable: bool = False,
    error_code: str | None = None,
    result: dict | None = None,
) -> dict:
    payload = {
        "request_id": request_id,
        "status": status,
        "message": message,
        "retryable": retryable,
    }
    if error_code is not None:
        payload["error_code"] = error_code
    payload["result"] = result or {}
    return payload
