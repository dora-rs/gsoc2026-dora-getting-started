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


def main() -> None:
    rclpy.init()
    ros_node = rclpy.create_node("week11_dora_agent_activity")
    publisher = ros_node.create_publisher(
        String, "/week11/agent_activity", 10
    )
    dora = Node()
    try:
        for event in dora:
            if event["type"] == "STOP":
                break
            if event["type"] != "INPUT" or event["id"] != "activity":
                continue
            request = read_json_event(event)
            publisher.publish(String(data=request["message"]))
            rclpy.spin_once(ros_node, timeout_sec=0.05)
            send_json(
                dora,
                "result",
                {
                    "request_id": request["request_id"],
                    "status": "succeeded",
                    "retryable": False,
                    "error_code": None,
                    "message": "Agent activity displayed in Webots.",
                    "result": {"displayed": True},
                },
                "week11.action-result.v1",
            )
    finally:
        ros_node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
