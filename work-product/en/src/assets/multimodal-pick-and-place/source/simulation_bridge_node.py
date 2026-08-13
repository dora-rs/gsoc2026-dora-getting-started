#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pyarrow as pa
from dora import Node


PREFIX = "DORA_SIMULATION_RESULT "
root = Path(__file__).resolve().parent
worker_python = os.environ["MULTIMODAL_SIM_PYTHON"]
node = Node()
worker = subprocess.Popen(
    [worker_python, "-u", str(root / "simulation_worker.py")],
    cwd=root,
    env=os.environ.copy(),
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
)


def invoke(command: dict[str, object]) -> dict[str, object]:
    if worker.stdin is None or worker.stdout is None:
        raise RuntimeError("simulation worker pipes are unavailable")
    worker.stdin.write(json.dumps(command, separators=(",", ":")) + "\n")
    worker.stdin.flush()
    while True:
        line = worker.stdout.readline()
        if not line:
            raise RuntimeError(
                f"simulation worker exited before replying (code={worker.poll()})"
            )
        if line.startswith(PREFIX):
            response = json.loads(line[len(PREFIX) :])
            if not response.get("ok"):
                raise RuntimeError(
                    f"simulation worker failed: {response.get('error_type')}"
                )
            return response["result"]
        print(f"SIMULATION {line.rstrip()}", flush=True)


try:
    for event in node:
        if event["type"] == "STOP":
            break
        if event["type"] != "INPUT":
            continue
        command = json.loads(event["value"][0].as_py())
        if command["kind"] == "finish":
            invoke(command)
            break
        result = invoke(command)
        if command["kind"] == "capture":
            node.send_output("observation", pa.array([json.dumps(result)]))
        elif command["kind"] == "run_pick_place":
            node.send_output("motion_complete", pa.array([json.dumps(result)]))
finally:
    if worker.poll() is None:
        if worker.stdin is not None:
            worker.stdin.close()
        try:
            worker.wait(timeout=10)
        except subprocess.TimeoutExpired:
            worker.terminate()
            worker.wait(timeout=5)
