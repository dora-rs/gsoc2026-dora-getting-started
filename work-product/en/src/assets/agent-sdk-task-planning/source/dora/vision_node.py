#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

import cv2
import rclpy
from cv_bridge import CvBridge
from dora import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common import read_json_event, send_json
from week10_runtime.indicator_vision import classify_indicator


class VisionRuntime:
    def __init__(self):
        self.node = rclpy.create_node("week10_indicator_vision_runtime")
        self.bridge = CvBridge()
        self.image = None
        self.location = "unknown"
        self.node.create_subscription(
            Image, "/camera/image_raw", self._on_image, 10
        )
        self.node.create_subscription(
            String, "/week10/robot_state", self._on_state, 10
        )

    def _on_image(self, message):
        self.image = self.bridge.imgmsg_to_cv2(
            message, desired_encoding="bgr8"
        )

    def _on_state(self, message):
        try:
            self.location = json.loads(message.data).get(
                "location", "unknown"
            )
        except json.JSONDecodeError:
            return

    def observe(self, request):
        request_id = request["request_id"]
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            rclpy.spin_once(self.node, timeout_sec=0.1)
            if self.image is not None and self.location == "indicator_station":
                break
        if self.location != "indicator_station":
            return {
                "request_id": request_id,
                "status": "rejected",
                "retryable": False,
                "error_code": "WRONG_OBSERVATION_LOCATION",
                "message": "Robot must be at indicator_station.",
                "result": {},
            }
        if self.image is None:
            return {
                "request_id": request_id,
                "status": "failed",
                "retryable": True,
                "error_code": "CAMERA_UNAVAILABLE",
                "message": "No fresh RGB frame is available.",
                "result": {},
            }
        output_dir = Path(
            os.getenv("WEEK10_OUTPUT_DIR", "/workspace/outputs")
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_id = re.sub(r"[^A-Za-z0-9_.-]", "_", request_id)
        image_path = output_dir / f"{safe_id}-indicator.jpg"
        if not cv2.imwrite(str(image_path), self.image):
            return {
                "request_id": request_id,
                "status": "failed",
                "retryable": True,
                "error_code": "IMAGE_WRITE_FAILED",
                "message": "Could not save the RGB observation.",
                "result": {},
            }
        try:
            observation = classify_indicator(image_path)
        except Exception as error:
            return {
                "request_id": request_id,
                "status": "failed",
                "retryable": True,
                "error_code": "VLM_REQUEST_FAILED",
                "message": f"Indicator classification failed: {error}",
                "result": {"image": str(image_path)},
            }
        return {
            "request_id": request_id,
            "status": "succeeded",
            "retryable": False,
            "error_code": None,
            "message": "Indicator observation completed.",
            "result": {
                **observation.model_dump(),
                "image": str(image_path),
            },
        }


def main():
    rclpy.init()
    dora = Node()
    runtime = VisionRuntime()
    try:
        for event in dora:
            if event["type"] == "STOP":
                break
            if event["type"] != "INPUT" or event["id"] != "observe":
                continue
            result = runtime.observe(read_json_event(event))
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
