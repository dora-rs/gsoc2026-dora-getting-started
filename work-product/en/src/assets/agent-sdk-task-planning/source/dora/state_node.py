#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import rclpy
from dora import Node
from std_msgs.msg import String


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common import send_json
from agent_runtime.state_projection import public_robot_state


class StateRuntime:
    def __init__(self):
        self.node = rclpy.create_node("agent_state_runtime")
        self.latest = None
        self.node.create_subscription(
            String, "/agent_task/robot_state", self._on_state, 10
        )

    def _on_state(self, message):
        try:
            payload = json.loads(message.data)
            self.latest = public_robot_state(
                payload, captured_at=datetime.now(timezone.utc)
            )
        except (ValueError, TypeError):
            return

    def poll(self):
        rclpy.spin_once(self.node, timeout_sec=0.0)


def main():
    rclpy.init()
    dora = Node()
    runtime = StateRuntime()
    try:
        for event in dora:
            if event["type"] == "STOP":
                break
            if event["type"] != "INPUT" or event["id"] != "tick":
                continue
            runtime.poll()
            if runtime.latest is not None:
                send_json(
                    dora,
                    "state",
                    runtime.latest.model_dump(mode="json"),
                    "agent_task.robot-state.v1",
                )
    finally:
        runtime.node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
