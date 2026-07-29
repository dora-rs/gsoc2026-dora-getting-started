from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from robot_api.contracts import (
    ActionResponse,
    ArmPoseRequest,
    NavigateRequest,
    ObservationRequest,
    RobotState,
    StopRequest,
    require_fresh_state,
)


def state(**overrides):
    values = {
        "captured_at": datetime.now(timezone.utc),
        "location": "home",
        "arm_pose": "home",
        "navigation_active": False,
        "arm_active": False,
        "stopped": False,
        "pose": {"x": -2.8, "y": -1.8, "yaw": 0.0},
    }
    values.update(overrides)
    return RobotState(**values)


def test_named_requests_accept_only_allow_listed_values():
    assert NavigateRequest(location="main_switch").location == "main_switch"
    assert NavigateRequest(location="indicator_station").location == "indicator_station"
    assert ObservationRequest(target="status_indicator").target == "status_indicator"
    assert ArmPoseRequest(pose="ready").pose == "ready"
    assert StopRequest(reason="operator requested stop").reason

    with pytest.raises(ValidationError):
        NavigateRequest(location="x=3.15,y=0")
    with pytest.raises(ValidationError):
        ArmPoseRequest(pose="joint_1=0.4")


def test_raw_motion_fields_are_rejected():
    with pytest.raises(ValidationError):
        NavigateRequest(location="home", linear_velocity=0.5)
    with pytest.raises(ValidationError):
        ArmPoseRequest(pose="press", joint_angles=[0.0, 1.0])


def test_common_response_contains_correlated_fresh_robot_state():
    response = ActionResponse(
        request_id="req-001",
        action_id="act-001",
        status="succeeded",
        retryable=False,
        error_code=None,
        message="Reached named location.",
        robot_state=state(location="main_switch"),
        result={"location": "main_switch"},
    )

    assert response.request_id == "req-001"
    assert response.action_id == "act-001"
    assert response.robot_state.location == "main_switch"
    assert response.result == {"location": "main_switch"}


def test_failed_response_requires_an_error_code():
    with pytest.raises(ValidationError):
        ActionResponse(
            request_id="req-002",
            action_id="act-002",
            status="failed",
            retryable=True,
            message="Camera frame unavailable.",
            robot_state=state(),
        )


def test_cancelled_response_accepts_a_structured_error_code():
    response = ActionResponse(
        request_id="req-cancelled",
        action_id="act-cancelled",
        status="cancelled",
        retryable=True,
        error_code="ACTION_CANCELLED",
        message="Navigation was cancelled by a stop request.",
        robot_state=state(),
    )

    assert response.status == "cancelled"
    assert response.error_code == "ACTION_CANCELLED"


def test_state_freshness_is_enforced():
    stale = state(
        captured_at=datetime.now(timezone.utc) - timedelta(seconds=8)
    )
    with pytest.raises(ValueError, match="stale"):
        require_fresh_state(stale, max_age_seconds=2.0)

    assert require_fresh_state(state(), max_age_seconds=2.0).location == "home"
