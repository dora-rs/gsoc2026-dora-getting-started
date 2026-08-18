#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path

import pyarrow as pa
from dora import Node

from bridge_protocol import JsonLineWorker


root = Path(__file__).resolve().parent
result_path = Path("/workspace/outputs/mission-result.json")
node = Node()
worker = JsonLineWorker(
    [
        os.environ.get("NAVIGATION_ROS_PYTHON", "/usr/bin/python3"),
        "-u",
        str(root / "navigation_ros_worker.py"),
    ],
    cwd=root,
    env=os.environ.copy(),
    log=lambda line: print(f"NAVIGATION_WORKER {line}", flush=True),
)
result_written = False
try:
    for event in node:
        if event["type"] == "STOP":
            break
        if event["type"] != "INPUT":
            continue
        request = {"op": "step"}
        if event["id"] == "sensors":
            request["sensors"] = json.loads(event["value"].to_pylist()[0])
        payload = worker.request(request)
        node.send_output(
            "mission",
            pa.array([json.dumps(payload, separators=(",", ":"))]),
            {"schema": "navigation.mission.v1"},
        )
        if payload["state"] in ("SUCCEEDED", "FAILED") and not result_written:
            result_path.parent.mkdir(parents=True, exist_ok=True)
            result_path.write_text(
                json.dumps(payload, indent=2) + "\n", encoding="utf-8"
            )
            result_written = True
finally:
    worker.close()
