from datetime import datetime, timezone

from week10_runtime.protocol import (
    action_result,
    parse_controller_state,
)


def test_controller_state_is_converted_to_typed_utc_state():
    state = parse_controller_state(
        {
            "captured_at_unix_s": 1785283200.25,
            "location": "main_switch",
            "arm_pose": "ready",
            "switch_state": "on",
            "navigation_active": False,
            "arm_active": False,
            "stopped": False,
            "pose": {"x": 3.15, "y": 0.0, "yaw": 0.0},
        }
    )

    assert state.captured_at == datetime.fromtimestamp(
        1785283200.25, tz=timezone.utc
    )
    assert state.location == "main_switch"


def test_action_result_keeps_only_public_status_fields():
    result = action_result(
        "req-1",
        status="failed",
        message="camera unavailable",
        retryable=True,
        error_code="CAMERA_UNAVAILABLE",
        result={"frame": None},
    )

    assert result == {
        "request_id": "req-1",
        "status": "failed",
        "message": "camera unavailable",
        "retryable": True,
        "error_code": "CAMERA_UNAVAILABLE",
        "result": {"frame": None},
    }
