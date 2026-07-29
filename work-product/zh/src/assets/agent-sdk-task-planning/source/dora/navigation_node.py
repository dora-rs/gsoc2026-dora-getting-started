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


class NavigationRuntime:
    def __init__(self):
        self.node = rclpy.create_node("week10_navigation_runtime")
        self.status = None
        self.command = self.node.create_publisher(
            String, "/week10/nav_command", 10
        )
        self.node.create_subscription(
            String, "/week10/nav_status", self._on_status, 10
        )

    def _on_status(self, message):
        try:
            self.status = json.loads(message.data)
        except json.JSONDecodeError:
            return

    def navigate(self, request):
        request_id = request["request_id"]
        self.status = None
        self.command.publish(
            String(
                data=json.dumps(
                    {
                        "request_id": request_id,
                        "action": "navigate_to",
                        "location": request["location"],
                    },
                    separators=(",", ":"),
                )
            )
        )
        deadline = time.monotonic() + float(
            os.getenv("WEEK10_NAVIGATION_TIMEOUT_S", "180")
        )
        while time.monotonic() < deadline:
            rclpy.spin_once(self.node, timeout_sec=0.1)
            status = self.status
            if not status or status.get("request_id") != request_id:
                continue
            if status["status"] == "running":
                continue
            succeeded = status["status"] == "succeeded"
            error_code = None
            if status["status"] == "cancelled":
                error_code = "ACTION_CANCELLED"
            elif not succeeded:
                error_code = "NAVIGATION_REJECTED"
            return {
                "request_id": request_id,
                "status": "succeeded" if succeeded else status["status"],
                "retryable": status["status"] == "failed",
                "error_code": error_code,
                "message": status["detail"],
                "result": {"location": status.get("location")},
            }
        return {
            "request_id": request_id,
            "status": "failed",
            "retryable": True,
            "error_code": "NAVIGATION_TIMEOUT",
            "message": "Named navigation timed out.",
            "result": {},
        }

def main():
    rclpy.init()
    dora = Node()
    runtime = NavigationRuntime()
    try:
        for event in dora:
            if event["type"] == "STOP":
                break
            if event["type"] != "INPUT":
                continue
            if event["id"] == "navigate":
                result = runtime.navigate(read_json_event(event))
                send_json(
                    dora,
                    "result",
                    result,
                    "week10.action-result.v1",
                )
    finally:
        runtime.node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
