from __future__ import annotations

import json

import pyarrow as pa


def read_json_event(event) -> dict:
    values = event["value"].to_pylist()
    if len(values) != 1 or not isinstance(values[0], str):
        raise ValueError("Dora event must contain one JSON string")
    value = json.loads(values[0])
    if not isinstance(value, dict):
        raise TypeError("Dora event JSON must be an object")
    return value


def send_json(node, output: str, payload: dict, schema: str) -> None:
    node.send_output(
        output,
        pa.array([json.dumps(payload, separators=(",", ":"))]),
        {"schema": schema},
    )
