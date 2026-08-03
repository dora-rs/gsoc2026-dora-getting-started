import threading
import time
from datetime import datetime, timezone

from robot_api.contracts import RobotState
from robot_api.dora_broker import DoraBroker


def state(location="home", **overrides):
    values = {
        "captured_at": datetime.now(timezone.utc),
        "location": location,
        "arm_pose": "home",
        "navigation_active": False,
        "arm_active": False,
        "stopped": False,
        "pose": {"x": -2.8, "y": -1.8, "yaw": 0.0},
    }
    values.update(overrides)
    return RobotState(
        **values,
    )


def test_broker_correlates_dora_result_with_waiting_http_request():
    broker = DoraBroker(state(), timeout_seconds={"navigate": 1.0})
    holder = {}

    def call():
        holder["response"] = broker.execute(
            "navigate",
            {"location": "main_switch"},
            request_id="req-10",
            action_id="act-10",
        )

    thread = threading.Thread(target=call)
    thread.start()
    dispatch = None
    for _ in range(50):
        pending = broker.drain()
        if pending:
            dispatch = pending[0]
            break
        time.sleep(0.01)

    assert dispatch.request_id == "req-10"
    assert dispatch.kind == "navigate"
    broker.update_state(state(location="main_switch"))
    broker.resolve(
        {
            "request_id": "req-10",
            "status": "succeeded",
            "message": "Reached main_switch.",
            "result": {"location": "main_switch"},
        }
    )
    thread.join(timeout=1)

    assert holder["response"].status == "succeeded"
    assert holder["response"].robot_state.location == "main_switch"


def test_success_waits_for_matching_post_action_state():
    broker = DoraBroker(state(), timeout_seconds={"navigate": 1.0})
    holder = {}

    def call():
        holder["response"] = broker.execute(
            "navigate",
            {"location": "main_switch"},
            request_id="req-state-sync",
            action_id="act-state-sync",
        )

    thread = threading.Thread(target=call)
    thread.start()
    for _ in range(50):
        if broker.drain():
            break
        time.sleep(0.01)

    broker.resolve(
        {
            "request_id": "req-state-sync",
            "status": "succeeded",
            "message": "Reached main_switch.",
            "result": {"location": "main_switch"},
        }
    )
    time.sleep(0.02)

    assert thread.is_alive()

    broker.update_state(state(location="main_switch"))
    thread.join(timeout=1)

    assert holder["response"].status == "succeeded"
    assert holder["response"].robot_state.location == "main_switch"


def test_cancelled_navigation_waits_for_stopped_motion_state():
    broker = DoraBroker(
        state(navigation_active=True),
        timeout_seconds={"navigate": 1.0},
    )
    holder = {}

    def call():
        holder["response"] = broker.execute(
            "navigate",
            {"location": "main_switch"},
            request_id="req-cancel-sync",
            action_id="act-cancel-sync",
        )

    thread = threading.Thread(target=call)
    thread.start()
    for _ in range(50):
        if broker.drain():
            break
        time.sleep(0.01)

    broker.resolve(
        {
            "request_id": "req-cancel-sync",
            "status": "cancelled",
            "retryable": False,
            "error_code": "ACTION_CANCELLED",
            "message": "Stopped by operator.",
            "result": {"location": "home"},
        }
    )
    time.sleep(0.02)
    assert thread.is_alive()

    broker.update_state(
        state(navigation_active=False, stopped=True)
    )
    thread.join(timeout=1)

    assert holder["response"].status == "cancelled"
    assert holder["response"].robot_state.navigation_active is False
    assert holder["response"].robot_state.stopped is True


def test_broker_times_out_with_retryable_structured_failure():
    broker = DoraBroker(state(), timeout_seconds={"observe": 0.02})

    response = broker.execute(
        "observe",
        {"target": "status_indicator"},
        request_id="req-timeout",
        action_id="act-timeout",
    )

    assert response.status == "failed"
    assert response.error_code == "ACTION_TIMEOUT"
    assert response.retryable is True


def test_unknown_or_duplicate_results_are_ignored():
    broker = DoraBroker(state())
    assert broker.resolve({"request_id": "missing", "status": "succeeded"}) is False


def test_duplicate_request_returns_without_locking_the_broker():
    broker = DoraBroker(state(), timeout_seconds={"navigate": 0.2})

    first = threading.Thread(
        target=lambda: broker.execute(
            "navigate",
            {"location": "indicator_station"},
            request_id="req-duplicate",
            action_id="act-first",
        ),
        daemon=True,
    )
    first.start()
    for _ in range(50):
        if broker.drain():
            break
        time.sleep(0.01)

    holder = {}
    duplicate = threading.Thread(
        target=lambda: holder.setdefault(
            "response",
            broker.execute(
                "navigate",
                {"location": "indicator_station"},
                request_id="req-duplicate",
                action_id="act-duplicate",
            ),
        ),
        daemon=True,
    )
    duplicate.start()
    duplicate.join(timeout=0.1)

    assert not duplicate.is_alive()
    assert holder["response"].error_code == "DUPLICATE_REQUEST"
