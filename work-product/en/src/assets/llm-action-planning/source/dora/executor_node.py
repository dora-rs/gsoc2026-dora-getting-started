#!/usr/bin/env python3
import json
import os
import sys
import time
from pathlib import Path

import pyarrow as pa
import rclpy
from dora import Node


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from action_planning.mission import MissionMachine
from action_planning.ros_skills import RosSkillRuntime


def send_status(node, payload):
    node.send_output(
        "status",
        pa.array([json.dumps(payload, separators=(",", ":"))]),
        {"schema": "action_planning.mission-status.v1"},
    )


def emit_status(node, audit_path, payload):
    stamped = {
        "recorded_at_unix_s": round(time.time(), 6),
        **payload,
    }
    with audit_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(stamped, separators=(",", ":")) + "\n")
    send_status(node, stamped)


def main():
    output_dir = Path(os.getenv("ACTION_PLANNING_OUTPUT_DIR", "/workspace/outputs"))
    result_path = output_dir / "mission-result.json"
    audit_path = output_dir / "mission-audit.jsonl"
    output_dir.mkdir(parents=True, exist_ok=True)
    audit_path.write_text("", encoding="utf-8")
    dora = Node()
    rclpy.init()
    runtime = RosSkillRuntime(output_dir)
    runtime.wait_until_ready()
    try:
        for event in dora:
            if event["type"] == "STOP":
                break
            if event["type"] != "INPUT" or event["id"] != "plan":
                continue
            plan = json.loads(event["value"].to_pylist()[0])
            machine = MissionMachine(plan)
            emit_status(
                dora,
                audit_path,
                {"event": "PLAN_ACCEPTED", "plan": plan, "state": machine.state},
            )
            while machine.state not in {"SUCCEEDED", "FAILED"}:
                request = machine.next_request()
                if request is None:
                    break
                emit_status(
                    dora,
                    audit_path,
                    {
                        "event": "SKILL_STARTED",
                        "step_id": request.step_id,
                        "skill": request.skill,
                        "arguments": request.arguments,
                    },
                )
                result = runtime.execute(
                    request.step_id, request.skill, request.arguments
                )
                machine.accept_result(request.step_id, result)
                emit_status(
                    dora,
                    audit_path,
                    {
                        "event": "SKILL_FINISHED",
                        "step_id": request.step_id,
                        "skill": request.skill,
                        "result": result,
                        "state": machine.state,
                    },
                )
            machine.next_request()
            payload = {
                "event": "MISSION_FINISHED",
                "state": machine.state,
                "context": machine.context,
                "events": machine.events,
            }
            result_path.write_text(
                json.dumps(payload, indent=2) + "\n", encoding="utf-8"
            )
            emit_status(dora, audit_path, payload)
    finally:
        runtime.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
