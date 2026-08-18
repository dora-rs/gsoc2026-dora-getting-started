#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import rclpy
from dora import Node
from std_msgs.msg import String


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common import read_json_event, send_json


class ArmRuntime:
    def __init__(self):
        self.node = rclpy.create_node("agent_arm_runtime")
        self.status = None
        self.command = self.node.create_publisher(
            String, "/agent_task/arm_command", 10
        )
        self.node.create_subscription(
            String, "/agent_task/arm_status", self._on_status, 10
        )

    def _on_status(self, message):
        try:
            self.status = json.loads(message.data)
        except json.JSONDecodeError:
            return

    def move(self, request):
        request_id = request["request_id"]
        self.status = None
        self.command.publish(
            String(
                data=json.dumps(
                    {
                        "request_id": request_id,
                        "action": "move_arm_to_named_pose",
                        "pose": request["pose"],
                    },
                    separators=(",", ":"),
                )
            )
        )
        deadline = time.monotonic() + float(
            os.getenv("AGENT_TASK_ARM_TIMEOUT_S", "75")
        )
        while time.monotonic() < deadline:
            rclpy.spin_once(self.node, timeout_sec=0.1)
            status = self.status
            if not status or status.get("request_id") != request_id:
                continue
            if status["status"] == "running":
                continue
            succeeded = status["status"] == "succeeded"
            return {
                "request_id": request_id,
                "status": "succeeded" if succeeded else status["status"],
                "retryable": status["status"] == "failed",
                "error_code": None if succeeded else "ARM_ACTION_REJECTED",
                "message": status["detail"],
                "result": {"pose": status.get("arm_pose")},
            }
        return {
            "request_id": request_id,
            "status": "failed",
            "retryable": True,
            "error_code": "ARM_ACTION_TIMEOUT",
            "message": "Named arm action timed out.",
            "result": {},
        }


def main():
    rclpy.init()
    dora = Node()
    runtime = ArmRuntime()
    try:
        for event in dora:
            if event["type"] == "STOP":
                break
            if event["type"] != "INPUT" or event["id"] != "move":
                continue
            result = runtime.move(read_json_event(event))
            send_json(
                dora,
                "result",
                result,
                "agent_task.action-result.v1",
            )
    finally:
        runtime.node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
