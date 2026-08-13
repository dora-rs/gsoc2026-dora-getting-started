import threading
import time

from process_api.broker import DoraActionBroker


def test_broker_dispatches_and_resolves_action() -> None:
    broker = DoraActionBroker(
        {
            "observer": {"location": "home"},
            "operator": {"location": "home"},
            "process": {},
        },
        timeout_seconds={"navigate": 1.0},
    )
    result = {}

    def execute() -> None:
        result["response"] = broker.execute(
            "navigate",
            {"role": "observer", "location": "station"},
            request_id="req-1",
        )

    thread = threading.Thread(target=execute)
    thread.start()
    deadline = time.monotonic() + 0.5
    dispatches = []
    while time.monotonic() < deadline and not dispatches:
        dispatches = broker.drain()
        time.sleep(0.01)

    assert dispatches[0].kind == "navigate"
    assert dispatches[0].request_id == "req-1"
    assert broker.resolve(
        {
            "request_id": "req-1",
            "status": "succeeded",
            "retryable": False,
            "error_code": None,
            "message": "observer reached station",
            "result": {"location": "station"},
        }
    )
    thread.join(timeout=1.0)

    assert result["response"]["status"] == "succeeded"
    assert result["response"]["result"]["location"] == "station"
