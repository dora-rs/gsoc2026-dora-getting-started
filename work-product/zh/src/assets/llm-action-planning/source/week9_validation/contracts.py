from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


PLAN_SCHEMA = "week9.action-plan.v1"
OBSERVATION_SCHEMA = "week9.switch-observation.v1"
SKILL_REQUEST_SCHEMA = "week9.skill-request.v1"
SKILL_RESULT_SCHEMA = "week9.skill-result.v1"


@dataclass(frozen=True)
class SwitchObservation:
    switch_id: str
    visible: bool
    state: str
    confidence: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": OBSERVATION_SCHEMA,
            "switch_id": self.switch_id,
            "visible": self.visible,
            "state": self.state,
            "confidence": self.confidence,
        }


def parse_json_object(payload: str) -> dict[str, Any]:
    value = json.loads(payload)
    if not isinstance(value, dict):
        raise TypeError("payload must be a JSON object")
    return value


def parse_switch_observation(payload: str | dict[str, Any]) -> SwitchObservation:
    value = parse_json_object(payload) if isinstance(payload, str) else payload
    required = {"switch_id", "visible", "state", "confidence"}
    allowed = required | {"schema"}
    if set(value) - allowed or not required.issubset(value):
        raise ValueError("switch observation has unexpected fields")
    if "schema" in value and value["schema"] != OBSERVATION_SCHEMA:
        raise ValueError("unsupported switch observation schema")
    if value["switch_id"] != "main_switch":
        raise ValueError("unsupported switch ID")
    if type(value["visible"]) is not bool:
        raise TypeError("visible must be a boolean")
    if value["state"] not in {"on", "off", "unknown"}:
        raise ValueError("state must be on, off, or unknown")
    confidence = value["confidence"]
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise TypeError("confidence must be a number")
    if not 0.0 <= float(confidence) <= 1.0:
        raise ValueError("confidence must be between 0 and 1")
    return SwitchObservation(
        switch_id=value["switch_id"],
        visible=value["visible"],
        state=value["state"],
        confidence=float(confidence),
    )
