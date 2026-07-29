from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from robot_api.contracts import ActionResponse, RobotState
from robot_api.gateway import MemoryBroker, create_app


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


def test_named_navigation_returns_correlated_state():
    broker = MemoryBroker(state())
    client = TestClient(create_app(broker))

    response = client.post(
        "/v1/actions/navigate",
        headers={"X-Request-ID": "tutorial-001"},
        json={"location": "main_switch"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["request_id"] == "tutorial-001"
    assert payload["action_id"]
    assert payload["status"] == "succeeded"
    assert payload["robot_state"]["location"] == "main_switch"
    assert broker.calls[-1]["kind"] == "navigate"


def test_gateway_rejects_raw_motion_fields_before_dispatch():
    broker = MemoryBroker(state())
    client = TestClient(create_app(broker))

    response = client.post(
        "/v1/actions/navigate",
        json={"location": "home", "linear_velocity": 0.8},
    )

    assert response.status_code == 422
    assert broker.calls == []


def test_gateway_refuses_actions_when_robot_state_is_stale():
    broker = MemoryBroker(
        state(captured_at=datetime.now(timezone.utc) - timedelta(seconds=8))
    )
    client = TestClient(create_app(broker, max_state_age_seconds=2.0))

    response = client.post(
        "/v1/actions/arm",
        json={"pose": "ready"},
    )

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "failed"
    assert payload["error_code"] == "STATE_STALE"
    assert payload["retryable"] is True
    assert broker.calls == []


def test_action_result_can_be_queried_by_action_id():
    broker = MemoryBroker(state())
    client = TestClient(create_app(broker))
    created = client.post(
        "/v1/actions/observe",
        json={"target": "status_indicator"},
    ).json()

    response = client.get(f"/v1/actions/{created['action_id']}")

    assert response.status_code == 200
    assert ActionResponse.model_validate(response.json()).action_id == created[
        "action_id"
    ]


def test_stop_is_available_even_when_state_is_stale():
    broker = MemoryBroker(
        state(captured_at=datetime.now(timezone.utc) - timedelta(seconds=20))
    )
    client = TestClient(create_app(broker))

    response = client.post(
        "/v1/stop",
        json={"reason": "operator requested stop"},
    )

    assert response.status_code == 200
    assert response.json()["robot_state"]["stopped"] is True
