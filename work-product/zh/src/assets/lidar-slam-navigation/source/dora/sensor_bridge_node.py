#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path

import pyarrow as pa
from dora import Node

from bridge_protocol import JsonLineWorker


root = Path(__file__).resolve().parent
node = Node()
worker = JsonLineWorker(
    [
        os.environ.get("NAVIGATION_ROS_PYTHON", "/usr/bin/python3"),
        "-u",
        str(root / "sensor_ros_worker.py"),
    ],
    cwd=root,
    env=os.environ.copy(),
    log=lambda line: print(f"SENSOR_WORKER {line}", flush=True),
)
try:
    for event in node:
        if event["type"] == "STOP":
            break
        if event["type"] != "INPUT" or event["id"] != "tick":
            continue
        payload = worker.request({"op": "snapshot"})
        node.send_output(
            "status",
            pa.array([json.dumps(payload, separators=(",", ":"))]),
            {"schema": "navigation.sensor-status.v1"},
        )
finally:
    worker.close()
