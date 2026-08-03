from __future__ import annotations

import base64
import json
import os
import urllib.request
from pathlib import Path

from contracts import ObservationResult, parse_observation


MODEL = os.environ.get("OLLAMA_MODEL", "qwen3-vl:8b-instruct")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
PROMPT = """Inspect this RGB image from a robot wrist camera.

Return whether the red cube and blue cube are visible, and whether the red cube
is resting on top of the blue cube. Set red_on_blue to true only when the red
cube is vertically above the blue cube, their horizontal footprints overlap,
and the blue cube visibly supports the red cube. Return JSON only."""

SCHEMA = {
    "type": "object",
    "properties": {
        "red_visible": {"type": "boolean"},
        "blue_visible": {"type": "boolean"},
        "red_on_blue": {"type": "boolean"},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
    },
    "required": ["red_visible", "blue_visible", "red_on_blue", "confidence"],
    "additionalProperties": False,
}


def analyze_image(image_path: Path, timeout: float = 120.0) -> ObservationResult:
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    body = json.dumps(
        {
            "model": MODEL,
            "messages": [
                {"role": "user", "content": PROMPT, "images": [encoded]}
            ],
            "format": SCHEMA,
            "stream": False,
            "options": {"temperature": 0, "num_predict": 128},
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.load(response)
    content = payload.get("message", {}).get("content")
    if not isinstance(content, str):
        raise ValueError("model response does not contain message content")
    return parse_observation(content)


def result_dict(result: ObservationResult) -> dict[str, object]:
    return {
        "red_visible": result.red_visible,
        "blue_visible": result.blue_visible,
        "red_on_blue": result.red_on_blue,
        "confidence": result.confidence,
    }
