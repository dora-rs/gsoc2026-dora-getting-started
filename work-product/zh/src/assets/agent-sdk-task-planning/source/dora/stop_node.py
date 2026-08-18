#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

import rclpy
from dora import Node
from std_msgs.msg import String


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common import read_json_event, send_json


def main():
    rclpy.init()
    ros_node = rclpy.create_node("agent_stop_runtime")
    publisher = ros_node.create_publisher(String, "/agent_task/stop", 10)
    dora = Node()
    try:
        for event in dora:
            if event["type"] == "STOP":
                break
            if event["type"] != "INPUT" or event["id"] != "stop":
                continue
            request = read_json_event(event)
            publisher.publish(
                String(data=request.get("reason", "stop requested"))
            )
            for _ in range(5):
                rclpy.spin_once(ros_node, timeout_sec=0.05)
            send_json(
                dora,
                "result",
                {
                    "request_id": request["request_id"],
                    "status": "succeeded",
                    "retryable": False,
                    "error_code": None,
                    "message": "Stop request delivered to the robot controller.",
                    "result": {"stopped": True},
                },
                "agent_task.action-result.v1",
            )
    finally:
        ros_node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
