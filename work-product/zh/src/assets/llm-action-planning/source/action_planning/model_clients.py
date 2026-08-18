from __future__ import annotations

import base64
import json
import os
import urllib.request
from pathlib import Path
from typing import Any

from .contracts import PLAN_SCHEMA, parse_switch_observation
from .plan_validator import validate_plan


OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
MODEL = os.environ.get("OLLAMA_MODEL", "qwen3-vl:8b-instruct")

CONDITION_LEAF = {
    "type": "object",
    "properties": {
        "ref": {"type": "string"},
        "op": {"enum": ["eq", "ne"]},
        "value": {
            "oneOf": [
                {"type": "string"},
                {"type": "boolean"},
                {"type": "number"},
            ]
        },
    },
    "required": ["ref", "op", "value"],
    "additionalProperties": False,
}

PLAN_FORMAT = {
    "type": "object",
    "properties": {
        "schema": {"const": PLAN_SCHEMA},
        "goal": {"type": "string"},
        "steps": {
            "type": "array",
            "minItems": 1,
            "maxItems": 8,
            "items": {
                "oneOf": [
                    {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "skill": {"const": "navigate_to"},
                            "arguments": {
                                "type": "object",
                                "properties": {
                                    "location": {
                                        "enum": ["home", "main_switch"]
                                    }
                                },
                                "required": ["location"],
                                "additionalProperties": False,
                            },
                        },
                        "required": ["id", "skill", "arguments"],
                        "additionalProperties": False,
                    },
                    {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "skill": {"const": "observe_switch"},
                            "arguments": {
                                "type": "object",
                                "properties": {
                                    "switch_id": {"const": "main_switch"}
                                },
                                "required": ["switch_id"],
                                "additionalProperties": False,
                            },
                            "save_as": {"type": "string"},
                            "when": {
                                "oneOf": [
                                    CONDITION_LEAF,
                                    {
                                        "type": "object",
                                        "properties": {
                                            "all": {
                                                "type": "array",
                                                "items": CONDITION_LEAF,
                                            }
                                        },
                                        "required": ["all"],
                                        "additionalProperties": False,
                                    },
                                ]
                            },
                        },
                        "required": ["id", "skill", "arguments"],
                        "additionalProperties": False,
                    },
                    {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "skill": {"const": "set_switch_state"},
                            "arguments": {
                                "type": "object",
                                "properties": {
                                    "switch_id": {"const": "main_switch"},
                                    "state": {"enum": ["on", "off"]},
                                },
                                "required": ["switch_id", "state"],
                                "additionalProperties": False,
                            },
                            "when": {
                                "oneOf": [
                                    CONDITION_LEAF,
                                    {
                                        "type": "object",
                                        "properties": {
                                            "all": {
                                                "type": "array",
                                                "items": CONDITION_LEAF,
                                            }
                                        },
                                        "required": ["all"],
                                        "additionalProperties": False,
                                    },
                                ]
                            },
                        },
                        "required": ["id", "skill", "arguments", "when"],
                        "additionalProperties": False,
                    },
                ]
            },
        },
    },
    "required": ["schema", "goal", "steps"],
    "additionalProperties": False,
}

OBSERVATION_FORMAT = {
    "type": "object",
    "properties": {
        "switch_id": {"const": "main_switch"},
        "visible": {"type": "boolean"},
        "state": {"enum": ["on", "off", "unknown"]},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
    },
    "required": ["switch_id", "visible", "state", "confidence"],
    "additionalProperties": False,
}


def _chat(
    messages: list[dict[str, Any]],
    output_format: dict[str, Any],
    timeout: float,
) -> dict[str, Any]:
    body = json.dumps(
        {
            "model": MODEL,
            "messages": messages,
            "format": output_format,
            "stream": False,
            "options": {"temperature": 0, "num_predict": 768},
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
    value = json.loads(content)
    if not isinstance(value, dict):
        raise TypeError("model response must be a JSON object")
    return value


def request_action_plan(
    task: str,
    skill_manifest: dict[str, Any],
    timeout: float = 120.0,
) -> dict[str, Any]:
    prompt = f"""Create one complete conditional robot action plan.

Task: {task}

Available skill manifest:
{json.dumps(skill_manifest, indent=2)}

Rules:
- Return JSON only and use schema {PLAN_SCHEMA}.
- Use only skills and named arguments from the manifest.
- Use exactly five steps in this order:
  1. navigate_to with arguments {{"location":"main_switch"}} and no condition.
  2. observe_switch with arguments {{"switch_id":"main_switch"}}, save_as "before",
     and no condition.
  3. set_switch_state with arguments
     {{"switch_id":"main_switch","state":"off"}} and an "all" condition containing
     {{"ref":"before.visible","op":"eq","value":true}} and
     {{"ref":"before.state","op":"eq","value":"on"}}.
  4. observe_switch with arguments {{"switch_id":"main_switch"}} and an "all"
     condition containing {{"ref":"turn_off.status","op":"eq","value":"succeeded"}}.
  5. navigate_to with arguments {{"location":"home"}} and no condition.
- Use the exact step id "turn_off" for step 3.
- If the switch is already off, the conditions skip steps 3 and 4.
- Do not emit coordinates, velocities, joint angles, motor commands, code, or shell commands.
"""
    plan = _chat([{"role": "user", "content": prompt}], PLAN_FORMAT, timeout)
    validate_plan(plan).require_valid()
    return plan


def observe_switch(image_path: Path, timeout: float = 120.0) -> dict[str, Any]:
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    prompt = """Inspect this RGB image from a mobile manipulator.

The target is the wall panel named main_switch. Its lever has two clearly
separated positions. Judge the indicator by emitted brightness, not hue:
bright luminous green means on; an unlit black, gray, or very dark green
indicator means off.
Return whether the switch is visible and whether it is on, off, or unknown.
Use unknown when the panel is occluded or ambiguous. Return JSON only."""
    value = _chat(
        [
            {
                "role": "user",
                "content": prompt,
                "images": [encoded],
            }
        ],
        OBSERVATION_FORMAT,
        timeout,
    )
    observation = parse_switch_observation(value)
    return observation.as_dict()
