#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path

import pyarrow as pa
from dora import Node

from simulation_runtime import SimulationSession


root = Path(__file__).resolve().parent
output_dir = Path(os.environ.get("WEEK7_OUTPUT", root / "outputs" / "dora-run"))
trajectory_path = Path(
    os.environ.get("WEEK7_TRAJECTORY", root / "validated-trajectory.json")
)
session = SimulationSession(output_dir, trajectory_path)
node = Node()

try:
    for event in node:
        if event["type"] == "STOP":
            break
        if event["type"] != "INPUT":
            continue
        command = json.loads(event["value"][0].as_py())
        if command["kind"] == "capture":
            result = session.capture(command["phase"])
            node.send_output("observation", pa.array([json.dumps(result)]))
        elif command["kind"] == "run_pick_place":
            result = session.run_pick_place()
            node.send_output("motion_complete", pa.array([json.dumps(result)]))
        elif command["kind"] == "finish":
            break
finally:
    session.close()
