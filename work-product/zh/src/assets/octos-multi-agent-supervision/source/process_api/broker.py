from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Dispatch:
    kind: str
    payload: dict
    request_id: str


@dataclass
class _Pending:
    dispatch: Dispatch
    event: threading.Event = field(default_factory=threading.Event)
    response: dict | None = None


class DoraActionBroker:
    def __init__(
        self,
        initial_status: dict,
        *,
        timeout_seconds: dict[str, float] | None = None,
    ) -> None:
        self._status = initial_status
        self._timeouts = {
            "navigate": 45.0,
            "switch": 20.0,
            "observe": 120.0,
            "activity": 5.0,
            **(timeout_seconds or {}),
        }
        self._lock = threading.Lock()
        self._dispatches: deque[Dispatch] = deque()
        self._pending: dict[str, _Pending] = {}

    def latest_status(self) -> dict:
        with self._lock:
            return _copy_dict(self._status)

    def update_status(self, status: dict) -> None:
        with self._lock:
            self._status = _copy_dict(status)

    def execute(
        self, kind: str, payload: dict, *, request_id: str
    ) -> dict:
        dispatch = Dispatch(kind, _copy_dict(payload), request_id)
        pending = _Pending(dispatch)
        with self._lock:
            if request_id in self._pending:
                return _failure(
                    request_id,
                    "DUPLICATE_REQUEST",
                    "A request with this identifier is already running.",
                    retryable=False,
                )
            self._pending[request_id] = pending
            self._dispatches.append(dispatch)

        timeout = self._timeouts.get(kind, 30.0)
        if pending.event.wait(timeout):
            assert pending.response is not None
            return pending.response

        with self._lock:
            self._pending.pop(request_id, None)
        return _failure(
            request_id,
            "ACTION_TIMEOUT",
            f"{kind} did not finish within {timeout:.1f} seconds.",
            retryable=True,
        )

    def drain(self) -> list[Dispatch]:
        with self._lock:
            items = list(self._dispatches)
            self._dispatches.clear()
            return items

    def resolve(self, payload: dict) -> bool:
        request_id = payload.get("request_id")
        with self._lock:
            pending = self._pending.pop(request_id, None)
            if pending is None:
                return False
            pending.response = _copy_dict(payload)
        pending.event.set()
        return True


def _copy_dict(value: dict) -> dict:
    import copy

    return copy.deepcopy(value)


def _failure(
    request_id: str,
    error_code: str,
    message: str,
    *,
    retryable: bool,
) -> dict:
    return {
        "request_id": request_id,
        "status": "failed",
        "retryable": retryable,
        "error_code": error_code,
        "message": message,
        "result": {},
    }
