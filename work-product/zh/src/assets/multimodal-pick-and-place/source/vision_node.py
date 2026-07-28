#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import pyarrow as pa
from dora import Node

from vision_client import analyze_image, result_dict


node = Node()

for event in node:
    if event["type"] == "STOP":
        break
    if event["type"] != "INPUT":
        continue
    observation = json.loads(event["value"][0].as_py())
    phase = observation["phase"]
    try:
        result = analyze_image(Path(observation["wrist_path"]))
        payload = {"phase": phase, "result": result_dict(result)}
    except Exception as exc:
        payload = {"phase": phase, "error": type(exc).__name__}
    node.send_output("analysis", pa.array([json.dumps(payload)]))
    if phase == "after":
        break
