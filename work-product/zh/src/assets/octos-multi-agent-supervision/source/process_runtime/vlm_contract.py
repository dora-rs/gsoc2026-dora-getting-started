import json
from dataclasses import dataclass


@dataclass(frozen=True)
class TemperatureResult:
    visible: bool
    temperature_c: float | None
    confidence: float
    evidence: str


def build_temperature_vlm_request(
    *,
    encoded_image: str,
    model: str,
    prompt: str,
) -> dict:
    return {
        "model": model,
        "stream": False,
        "format": "json",
        "keep_alive": 0,
        "messages": [
            {
                "role": "user",
                "content": prompt,
                "images": [encoded_image],
            }
        ],
        "options": {"temperature": 0.0, "num_ctx": 4096},
    }


def parse_temperature_result(content: str) -> TemperatureResult:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as error:
        raise ValueError("VLM result is not valid JSON") from error
    if not isinstance(payload, dict):
        raise ValueError("VLM result must be a JSON object")

    visible = payload.get("visible")
    if not isinstance(visible, bool):
        raise ValueError("visible must be a boolean")
    temperature = payload.get("temperature_c")
    if visible and not isinstance(temperature, (int, float)):
        raise ValueError("temperature_c must be numeric when visible")
    if temperature is not None and not isinstance(temperature, (int, float)):
        raise ValueError("temperature_c must be numeric or null")

    confidence = payload.get("confidence")
    if (
        not isinstance(confidence, (int, float))
        or isinstance(confidence, bool)
        or not 0.0 <= float(confidence) <= 1.0
    ):
        raise ValueError("confidence must be between 0 and 1")
    evidence = payload.get("evidence")
    if not isinstance(evidence, str) or not evidence.strip():
        raise ValueError("evidence must be a non-empty string")

    return TemperatureResult(
        visible=visible,
        temperature_c=(
            float(temperature) if temperature is not None else None
        ),
        confidence=float(confidence),
        evidence=evidence.strip(),
    )
