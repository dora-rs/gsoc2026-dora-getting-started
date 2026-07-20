#!/usr/bin/env python3
from __future__ import annotations

import json

import pyarrow as pa
from dora import Node

from contracts import parse_observation
from controller import TaskController


node = Node()
controller = TaskController(min_confidence=0.8)


def send_command(kind: str, phase: str | None = None) -> None:
    payload = {"kind": kind}
    if phase is not None:
        payload["phase"] = phase
    node.send_output("command", pa.array([json.dumps(payload)]))


for command in controller.start():
    send_command(command.kind, command.detail)

for event in node:
    if event["type"] == "STOP":
        break
    if event["type"] != "INPUT":
        continue

    payload = json.loads(event["value"][0].as_py())
    if event["id"] == "analysis":
        phase = payload["phase"]
        if "error" in payload:
            print(f"TASK_FAILED phase={phase} error={payload['error']}", flush=True)
            send_command("finish")
            break
        result = parse_observation(json.dumps(payload["result"]))
        print(
            f"VISION_RESULT phase={phase} result={json.dumps(payload['result'])}",
            flush=True,
        )
        commands = controller.on_analysis(phase, result)
    elif event["id"] == "motion_complete":
        print(f"MOTION_RESULT {json.dumps(payload)}", flush=True)
        commands = controller.on_motion_complete(bool(payload["success"]))
    else:
        continue

    finished = False
    for command in commands:
        if command.kind == "capture":
            send_command("capture", command.detail)
        elif command.kind == "run_pick_place":
            send_command("run_pick_place")
        elif command.kind == "task_success":
            print("TASK_SUCCESS", flush=True)
            send_command("finish")
            finished = True
        elif command.kind == "task_failed":
            print(f"TASK_FAILED reason={command.detail}", flush=True)
            send_command("finish")
            finished = True
    if finished:
        break
