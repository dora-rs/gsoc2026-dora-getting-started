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


class CommandRuntime:
    def __init__(self) -> None:
        self.node = rclpy.create_node("week11_dora_command")
        self.nav_status = {"observer": None, "operator": None}
        self.arm_status = None
        self.nav_publishers = {
            role: self.node.create_publisher(
                String, f"/week11/{role}/nav_command", 10
            )
            for role in ("observer", "operator")
        }
        self.arm_publisher = self.node.create_publisher(
            String, "/week11/operator/arm_command", 10
        )
        for role in ("observer", "operator"):
            self.node.create_subscription(
                String,
                f"/week11/{role}/nav_status",
                lambda message, role=role: self._on_nav(role, message),
                10,
            )
        self.node.create_subscription(
            String,
            "/week11/operator/arm_status",
            self._on_arm,
            10,
        )

    def _on_nav(self, role: str, message: String) -> None:
        try:
            self.nav_status[role] = json.loads(message.data)
        except json.JSONDecodeError:
            return

    def _on_arm(self, message: String) -> None:
        try:
            self.arm_status = json.loads(message.data)
        except json.JSONDecodeError:
            return

    def execute(self, request: dict) -> dict:
        if request["kind"] == "navigate":
            return self._navigate(request)
        if request["kind"] == "switch":
            return self._switch(request)
        return failure(
            request["request_id"],
            "UNSUPPORTED_COMMAND",
            "Unsupported command kind.",
        )

    def _wait_for_status(
        self,
        *,
        request_id: str,
        getter,
        timeout_s: float,
    ) -> dict | None:
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            rclpy.spin_once(self.node, timeout_sec=0.1)
            status = getter()
            if not status or status.get("request_id") != request_id:
                continue
            if status.get("status") == "running":
                continue
            return status
        return None

    def _navigate(self, request: dict) -> dict:
        role = request["role"]
        request_id = request["request_id"]
        self.nav_status[role] = None
        self.nav_publishers[role].publish(
            String(
                data=json.dumps(
                    {
                        "action": "navigate_to",
                        "location": request["location"],
                        "request_id": request_id,
                    }
                )
            )
        )
        status = self._wait_for_status(
            request_id=request_id,
            getter=lambda: self.nav_status[role],
            timeout_s=float(os.getenv("WEEK11_NAV_TIMEOUT_S", "40")),
        )
        if status is None:
            return failure(
                request_id, "NAVIGATION_TIMEOUT", "Navigation timed out."
            )
        return from_robot_status(
            request_id,
            status,
            result={"role": role, "location": status.get("location")},
        )

    def _switch(self, request: dict) -> dict:
        request_id = request["request_id"]
        self.arm_status = None
        self.arm_publisher.publish(
            String(
                data=json.dumps(
                    {
                        "action": "set_switch",
                        "switch": request["switch"],
                        "enabled": request["enabled"],
                        "request_id": request_id,
                    }
                )
            )
        )
        status = self._wait_for_status(
            request_id=request_id,
            getter=lambda: self.arm_status,
            timeout_s=float(os.getenv("WEEK11_SWITCH_TIMEOUT_S", "18")),
        )
        if status is None:
            return failure(
                request_id, "SWITCH_TIMEOUT", "Switch action timed out."
            )
        result_key = (
            "cooling_on"
            if request["switch"] == "cooling"
            else "relief_open"
        )
        return from_robot_status(
            request_id,
            status,
            result={
                "switch": request["switch"],
                result_key: request["enabled"],
            },
        )


def from_robot_status(
    request_id: str, status: dict, *, result: dict
) -> dict:
    succeeded = status.get("status") == "succeeded"
    return {
        "request_id": request_id,
        "status": "succeeded" if succeeded else status.get("status", "failed"),
        "retryable": status.get("status") == "failed",
        "error_code": None if succeeded else "ROBOT_COMMAND_REJECTED",
        "message": status.get("detail", "Robot command finished."),
        "result": result if succeeded else {},
    }


def failure(request_id: str, code: str, message: str) -> dict:
    return {
        "request_id": request_id,
        "status": "failed",
        "retryable": True,
        "error_code": code,
        "message": message,
        "result": {},
    }


def main() -> None:
    rclpy.init()
    runtime = CommandRuntime()
    dora = Node()
    try:
        for event in dora:
            if event["type"] == "STOP":
                break
            if event["type"] != "INPUT" or event["id"] != "action":
                continue
            result = runtime.execute(read_json_event(event))
            send_json(
                dora, "result", result, "week11.action-result.v1"
            )
    finally:
        runtime.node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
