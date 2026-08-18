from __future__ import annotations

from typing import Literal, Protocol
from uuid import uuid4

from fastapi import FastAPI, Header
from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NavigateRequest(StrictModel):
    role: Literal["observer", "operator"]
    location: Literal["home", "station"]


class SwitchRequest(StrictModel):
    switch: Literal["cooling", "relief"]
    enabled: bool


class ObservationRequest(StrictModel):
    target: Literal["pressure", "temperature"]


class ActivityRequest(StrictModel):
    message: str = Field(min_length=1, max_length=96)


class Broker(Protocol):
    def latest_status(self) -> dict: ...

    def execute(
        self, kind: str, payload: dict, *, request_id: str
    ) -> dict: ...


class MemoryBroker:
    def __init__(self, initial_status: dict) -> None:
        self._status = initial_status
        self.calls: list[dict] = []

    def latest_status(self) -> dict:
        return self._status

    def execute(
        self, kind: str, payload: dict, *, request_id: str
    ) -> dict:
        self.calls.append({"kind": kind, "payload": payload})
        result: dict = {}
        if kind == "navigate":
            result = {
                "role": payload["role"],
                "location": payload["location"],
            }
        elif kind == "switch":
            result = {f"{payload['switch']}_on": payload["enabled"]}
            if payload["switch"] == "relief":
                result = {"relief_open": payload["enabled"]}
        elif kind == "observe" and payload["target"] == "temperature":
            result = {
                "visible": True,
                "temperature_c": 58.4,
                "confidence": 0.98,
            }
        elif kind == "observe":
            result = {"available": True, "pressure_kpa": 190.0}
        elif kind == "activity":
            result = {"displayed": True}
        return {
            "request_id": request_id,
            "status": "succeeded",
            "retryable": False,
            "error_code": None,
            "message": f"{kind} completed.",
            "result": result,
        }


def _sanitized(value):
    if isinstance(value, dict):
        return {
            key: _sanitized(item)
            for key, item in value.items()
            if key not in {"temperature_c", "pressure_kpa"}
        }
    if isinstance(value, list):
        return [_sanitized(item) for item in value]
    return value


def create_app(broker: Broker) -> FastAPI:
    app = FastAPI(title="Dora Process Supervision API", version="1.0")

    def dispatch(kind: str, payload: dict, request_id: str | None):
        return broker.execute(
            kind,
            payload,
            request_id=request_id or f"req-{uuid4().hex[:12]}",
        )

    @app.get("/health")
    def health():
        return {"status": "ok", "transport": "dora"}

    @app.get("/v1/status")
    def status():
        return _sanitized(broker.latest_status())

    @app.post("/v1/navigate")
    def navigate(
        request: NavigateRequest,
        request_id: str | None = Header(default=None, alias="X-Request-ID"),
    ):
        return dispatch("navigate", request.model_dump(), request_id)

    @app.post("/v1/switch")
    def switch(
        request: SwitchRequest,
        request_id: str | None = Header(default=None, alias="X-Request-ID"),
    ):
        return dispatch("switch", request.model_dump(), request_id)

    @app.post("/v1/observe")
    def observe(
        request: ObservationRequest,
        request_id: str | None = Header(default=None, alias="X-Request-ID"),
    ):
        return dispatch("observe", request.model_dump(), request_id)

    @app.post("/v1/activity")
    def activity(
        request: ActivityRequest,
        request_id: str | None = Header(default=None, alias="X-Request-ID"),
    ):
        return dispatch("activity", request.model_dump(), request_id)

    return app
