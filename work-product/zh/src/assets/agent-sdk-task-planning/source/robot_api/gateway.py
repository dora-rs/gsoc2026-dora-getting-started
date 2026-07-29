from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol
from uuid import uuid4

from fastapi import FastAPI, Header
from fastapi.responses import JSONResponse

from .contracts import (
    ActionResponse,
    ArmPoseRequest,
    NavigateRequest,
    ObservationRequest,
    RobotState,
    StopRequest,
    require_fresh_state,
)


class Broker(Protocol):
    def latest_state(self) -> RobotState: ...

    def execute(
        self,
        kind: str,
        payload: dict,
        *,
        request_id: str,
        action_id: str,
    ) -> ActionResponse: ...

    def action_result(self, action_id: str) -> ActionResponse | None: ...


class MemoryBroker:
    """Small deterministic broker used by tests and API examples."""

    def __init__(self, initial_state: RobotState):
        self._state = initial_state
        self.indicator_lit = True
        self.calls: list[dict] = []
        self._actions: dict[str, ActionResponse] = {}

    def latest_state(self) -> RobotState:
        return self._state

    def execute(
        self,
        kind: str,
        payload: dict,
        *,
        request_id: str,
        action_id: str,
    ) -> ActionResponse:
        self.calls.append({"kind": kind, "payload": payload})
        values = self._state.model_dump()
        values["captured_at"] = datetime.now(timezone.utc)
        result = {}
        message = f"{kind} completed."
        if kind == "navigate":
            values["location"] = payload["location"]
            result = {"location": payload["location"]}
        elif kind == "observe":
            result = {
                "target": payload["target"],
                "visible": True,
                "lit": self.indicator_lit,
                "confidence": 0.99,
            }
        elif kind == "arm":
            values["arm_pose"] = payload["pose"]
            result = {"pose": payload["pose"]}
        elif kind == "stop":
            values["stopped"] = True
            values["navigation_active"] = False
            values["arm_active"] = False
            result = {"stopped": True}
        self._state = RobotState.model_validate(values)
        response = ActionResponse(
            request_id=request_id,
            action_id=action_id,
            status="succeeded",
            retryable=False,
            message=message,
            robot_state=self._state,
            result=result,
        )
        self._actions[action_id] = response
        return response

    def action_result(self, action_id: str) -> ActionResponse | None:
        return self._actions.get(action_id)


def create_app(
    broker: Broker, *, max_state_age_seconds: float = 2.0
) -> FastAPI:
    app = FastAPI(title="Dora Atomic Robot API", version="1.0")

    def identifiers(request_id: str | None):
        return request_id or f"req-{uuid4().hex[:12]}", f"act-{uuid4().hex[:12]}"

    def stale_response(
        request_id: str, action_id: str, state: RobotState, error: ValueError
    ):
        payload = ActionResponse(
            request_id=request_id,
            action_id=action_id,
            status="failed",
            retryable=True,
            error_code="STATE_STALE",
            message=str(error),
            robot_state=state,
        )
        return JSONResponse(
            status_code=503,
            content=payload.model_dump(mode="json"),
        )

    def dispatch(kind: str, payload: dict, request_id: str | None):
        correlation_id, action_id = identifiers(request_id)
        state = broker.latest_state()
        try:
            require_fresh_state(
                state, max_age_seconds=max_state_age_seconds
            )
        except ValueError as error:
            return stale_response(correlation_id, action_id, state, error)
        return broker.execute(
            kind,
            payload,
            request_id=correlation_id,
            action_id=action_id,
        )

    @app.get("/v1/robot/state", response_model=RobotState)
    def robot_state():
        return broker.latest_state()

    @app.post("/v1/actions/navigate", response_model=ActionResponse)
    def navigate(
        request: NavigateRequest,
        request_id: str | None = Header(default=None, alias="X-Request-ID"),
    ):
        return dispatch("navigate", request.model_dump(), request_id)

    @app.post("/v1/actions/observe", response_model=ActionResponse)
    def observe(
        request: ObservationRequest,
        request_id: str | None = Header(default=None, alias="X-Request-ID"),
    ):
        return dispatch("observe", request.model_dump(), request_id)

    @app.post("/v1/actions/arm", response_model=ActionResponse)
    def arm(
        request: ArmPoseRequest,
        request_id: str | None = Header(default=None, alias="X-Request-ID"),
    ):
        return dispatch("arm", request.model_dump(), request_id)

    @app.get("/v1/actions/{action_id}", response_model=ActionResponse)
    def action_result(action_id: str):
        result = broker.action_result(action_id)
        if result is not None:
            return result
        state = broker.latest_state()
        return JSONResponse(
            status_code=404,
            content=ActionResponse(
                request_id=f"lookup-{uuid4().hex[:12]}",
                action_id=action_id,
                status="failed",
                retryable=False,
                error_code="ACTION_NOT_FOUND",
                message="No action exists with this identifier.",
                robot_state=state,
            ).model_dump(mode="json"),
        )

    @app.post("/v1/stop", response_model=ActionResponse)
    def stop(
        request: StopRequest,
        request_id: str | None = Header(default=None, alias="X-Request-ID"),
    ):
        correlation_id, action_id = identifiers(request_id)
        return broker.execute(
            "stop",
            request.model_dump(),
            request_id=correlation_id,
            action_id=action_id,
        )

    return app
