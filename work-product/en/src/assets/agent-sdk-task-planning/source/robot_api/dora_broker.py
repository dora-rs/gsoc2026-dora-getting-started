from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field

from .contracts import ActionResponse, RobotState


@dataclass(frozen=True)
class Dispatch:
    kind: str
    payload: dict
    request_id: str
    action_id: str


@dataclass
class _Pending:
    dispatch: Dispatch
    event: threading.Event = field(default_factory=threading.Event)
    response: ActionResponse | None = None
    terminal_payload: dict | None = None


class DoraBroker:
    def __init__(
        self,
        initial_state: RobotState,
        *,
        timeout_seconds: dict[str, float] | None = None,
    ):
        self._state = initial_state
        self._timeouts = {
            "navigate": 180.0,
            "arm": 75.0,
            "observe": 120.0,
            "stop": 15.0,
            **(timeout_seconds or {}),
        }
        self._lock = threading.Lock()
        self._dispatches: deque[Dispatch] = deque()
        self._pending: dict[str, _Pending] = {}
        self._actions: dict[str, ActionResponse] = {}

    def latest_state(self) -> RobotState:
        with self._lock:
            return self._state.model_copy(deep=True)

    def update_state(self, state: RobotState) -> None:
        completed: list[_Pending] = []
        with self._lock:
            self._state = state
            for request_id, pending in list(self._pending.items()):
                payload = pending.terminal_payload
                if payload is None or not self._state_matches_result(
                    pending.dispatch.kind, payload, state
                ):
                    continue
                self._pending.pop(request_id)
                self._complete_locked(pending, payload, state)
                completed.append(pending)
        for pending in completed:
            pending.event.set()

    def execute(
        self,
        kind: str,
        payload: dict,
        *,
        request_id: str,
        action_id: str,
    ) -> ActionResponse:
        dispatch = Dispatch(kind, payload, request_id, action_id)
        pending = _Pending(dispatch)
        duplicate_state = None
        with self._lock:
            if request_id in self._pending:
                duplicate_state = self._state.model_copy(deep=True)
            else:
                self._pending[request_id] = pending
                self._dispatches.append(dispatch)
        if duplicate_state is not None:
            return self._failure(
                dispatch,
                "DUPLICATE_REQUEST",
                "A request with this identifier is already running.",
                retryable=False,
                state=duplicate_state,
            )

        timeout = self._timeouts.get(kind, 30.0)
        if pending.event.wait(timeout):
            assert pending.response is not None
            return pending.response

        with self._lock:
            self._pending.pop(request_id, None)
        response = self._failure(
            dispatch,
            "ACTION_TIMEOUT",
            f"{kind} did not finish within {timeout:.1f} seconds.",
            retryable=True,
        )
        with self._lock:
            self._actions[action_id] = response
        return response

    def drain(self) -> list[Dispatch]:
        with self._lock:
            items = list(self._dispatches)
            self._dispatches.clear()
            return items

    def resolve(self, payload: dict) -> bool:
        request_id = payload.get("request_id")
        with self._lock:
            pending = self._pending.get(request_id)
            state = self._state.model_copy(deep=True)
        if pending is None:
            return False

        status = payload.get("status", "failed")
        if (
            status in {"succeeded", "cancelled"}
            and self._requires_state_sync(pending.dispatch.kind)
            and not self._state_matches_result(
                pending.dispatch.kind, payload, state
            )
        ):
            with self._lock:
                if request_id not in self._pending:
                    return False
                pending.terminal_payload = dict(payload)
            return True

        with self._lock:
            if self._pending.pop(request_id, None) is None:
                return False
            self._complete_locked(pending, payload, state)
        pending.event.set()
        return True

    def _complete_locked(
        self, pending: _Pending, payload: dict, state: RobotState
    ) -> None:
        status = payload.get("status", "failed")
        error_code = payload.get("error_code")
        if status in {"failed", "rejected", "cancelled"} and not error_code:
            error_code = "ROBOT_ACTION_FAILED"
        response = ActionResponse(
            request_id=pending.dispatch.request_id,
            action_id=pending.dispatch.action_id,
            status=status,
            retryable=bool(payload.get("retryable", False)),
            error_code=error_code,
            message=payload.get("message", f"{pending.dispatch.kind} finished."),
            robot_state=state,
            result=payload.get("result", {}),
        )
        pending.response = response
        self._actions[response.action_id] = response

    @staticmethod
    def _requires_state_sync(kind: str) -> bool:
        return kind in {"navigate", "arm", "stop"}

    @staticmethod
    def _state_matches_result(
        kind: str, payload: dict, state: RobotState
    ) -> bool:
        result = payload.get("result") or {}
        if kind == "navigate":
            return (
                state.location == result.get("location")
                and not state.navigation_active
            )
        if kind == "arm":
            return (
                state.arm_pose == result.get("pose")
                and not state.arm_active
            )
        if kind == "stop":
            return state.stopped is bool(result.get("stopped", True))
        return True

    def action_result(self, action_id: str) -> ActionResponse | None:
        with self._lock:
            return self._actions.get(action_id)

    def _failure(
        self,
        dispatch: Dispatch,
        error_code: str,
        message: str,
        *,
        retryable: bool,
        state: RobotState | None = None,
    ) -> ActionResponse:
        return ActionResponse(
            request_id=dispatch.request_id,
            action_id=dispatch.action_id,
            status="failed",
            retryable=retryable,
            error_code=error_code,
            message=message,
            robot_state=state if state is not None else self.latest_state(),
        )
