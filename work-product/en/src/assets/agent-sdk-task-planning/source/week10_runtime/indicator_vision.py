from __future__ import annotations

import base64
import json
import os
import urllib.request
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class IndicatorObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target: Literal["status_indicator"]
    visible: bool
    lit: bool | None
    confidence: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_visibility(self):
        if self.visible and self.lit is None:
            raise ValueError("visible indicator requires a boolean lit state")
        if not self.visible and self.lit is not None:
            raise ValueError("occluded indicator must use null lit state")
        return self


OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "target": {"const": "status_indicator"},
        "visible": {"type": "boolean"},
        "lit": {"type": ["boolean", "null"]},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
    },
    "required": ["target", "visible", "lit", "confidence"],
    "additionalProperties": False,
}


def classify_indicator(
    image_path: Path,
    *,
    base_url: str | None = None,
    model: str | None = None,
    timeout_seconds: float = 120.0,
) -> IndicatorObservation:
    endpoint = (base_url or os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")).rstrip(
        "/"
    )
    model_name = model or os.getenv("OLLAMA_MODEL", "qwen3-vl:8b-instruct")
    image = base64.b64encode(image_path.read_bytes()).decode("ascii")
    prompt = """Inspect the RGB image from a mobile robot.

Find the separate wall panel named status_indicator. It has one large circular
lamp. A bright emissive green disk means lit=true. A dark black or gray disk
means lit=false. Ignore the red mechanical switch at another station.
If the indicator is occluded or ambiguous, return visible=false and lit=null.
Return only JSON that matches the provided schema."""
    body = json.dumps(
        {
            "model": model_name,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [image],
                }
            ],
            "format": OUTPUT_SCHEMA,
            "stream": False,
            "options": {"temperature": 0, "num_predict": 192},
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{endpoint}/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        payload = json.load(response)
    content = payload.get("message", {}).get("content")
    if not isinstance(content, str):
        raise ValueError("model response does not contain message content")
    return IndicatorObservation.model_validate_json(content)
