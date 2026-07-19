from __future__ import annotations

import json
from dataclasses import dataclass


OBSERVATION_FIELDS = {
    "red_visible",
    "blue_visible",
    "red_on_blue",
    "confidence",
}


@dataclass(frozen=True)
class ObservationResult:
    red_visible: bool
    blue_visible: bool
    red_on_blue: bool
    confidence: float


def parse_observation(payload: str) -> ObservationResult:
    value = json.loads(payload)
    if not isinstance(value, dict) or set(value) != OBSERVATION_FIELDS:
        raise ValueError("observation result has unexpected fields")

    for field in ("red_visible", "blue_visible", "red_on_blue"):
        if type(value[field]) is not bool:
            raise TypeError(f"{field} must be a boolean")

    confidence = value["confidence"]
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise TypeError("confidence must be a number")
    if not 0.0 <= float(confidence) <= 1.0:
        raise ValueError("confidence must be between 0 and 1")

    return ObservationResult(
        red_visible=value["red_visible"],
        blue_visible=value["blue_visible"],
        red_on_blue=value["red_on_blue"],
        confidence=float(confidence),
    )
