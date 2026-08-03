from fastapi.testclient import TestClient

from week11_api.gateway import MemoryBroker, create_app


def _status() -> dict:
    return {
        "observer": {
            "location": "home",
            "docked": False,
            "navigation_active": False,
        },
        "operator": {
            "location": "home",
            "at_control": False,
            "navigation_active": False,
            "arm_active": False,
        },
        "process": {
            "cooling_on": False,
            "relief_open": False,
            "temperature_safe_max_c": 60.0,
            "pressure_safe_max_kpa": 200.0,
            "phase": "running",
        },
    }


def test_status_does_not_expose_hidden_process_truth() -> None:
    client = TestClient(create_app(MemoryBroker(_status())))

    response = client.get("/v1/status")

    assert response.status_code == 200
    body = response.json()
    assert "temperature_c" not in str(body)
    assert "pressure_kpa" not in str(body)
    assert body["process"]["temperature_safe_max_c"] == 60.0


def test_named_navigation_and_switch_actions_are_dispatched() -> None:
    broker = MemoryBroker(_status())
    client = TestClient(create_app(broker))

    navigation = client.post(
        "/v1/navigate",
        json={"role": "observer", "location": "station"},
    )
    switch = client.post(
        "/v1/switch",
        json={"switch": "cooling", "enabled": True},
    )

    assert navigation.status_code == 200
    assert navigation.json()["status"] == "succeeded"
    assert switch.status_code == 200
    assert switch.json()["result"]["cooling_on"]
    assert [call["kind"] for call in broker.calls] == [
        "navigate",
        "switch",
    ]


def test_invalid_robot_role_is_rejected_by_schema() -> None:
    client = TestClient(create_app(MemoryBroker(_status())))

    response = client.post(
        "/v1/navigate",
        json={"role": "supervisor", "location": "station"},
    )

    assert response.status_code == 422


def test_observation_target_is_explicit() -> None:
    broker = MemoryBroker(_status())
    client = TestClient(create_app(broker))

    response = client.post(
        "/v1/observe", json={"target": "temperature"}
    )

    assert response.status_code == 200
    assert response.json()["result"]["temperature_c"] == 58.4
    assert broker.calls[-1]["payload"] == {"target": "temperature"}
