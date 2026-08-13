#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
import os
import re
import sys
import time
from pathlib import Path

import cv2
import rclpy
import requests
from cv_bridge import CvBridge
from dora import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common import read_json_event, send_json
from process_runtime.observation_gate import (
    observer_is_docked,
    pressure_is_available,
)
from process_runtime.vlm_contract import (
    build_temperature_vlm_request,
    parse_temperature_result,
)


VLM_PROMPT = """
Inspect this simulated industrial temperature display.
Read only the large current temperature value shown in degrees Celsius.
Return one JSON object with exactly these keys:
visible (boolean), temperature_c (number or null), confidence (0 to 1),
and evidence (a short description of the visible digits).
Do not infer the value from the progress bar or from prior knowledge.
""".strip()


class ObservationRuntime:
    def __init__(self) -> None:
        self.node = rclpy.create_node("process_dora_observation")
        self.bridge = CvBridge()
        self.image = None
        self.image_sequence = 0
        self.observer_state = {}
        self.pressure = {}
        self.node.create_subscription(
            Image,
            "/process/observer/camera/image_raw",
            self._on_image,
            10,
        )
        self.node.create_subscription(
            String,
            "/process/observer/state",
            self._on_observer_state,
            10,
        )
        self.node.create_subscription(
            String,
            "/process/plant/pressure",
            self._on_pressure,
            10,
        )

    def _on_image(self, message: Image) -> None:
        self.image = self.bridge.imgmsg_to_cv2(
            message, desired_encoding="bgr8"
        )
        self.image_sequence += 1

    def _on_observer_state(self, message: String) -> None:
        try:
            self.observer_state = json.loads(message.data)
        except json.JSONDecodeError:
            return

    def _on_pressure(self, message: String) -> None:
        try:
            self.pressure = json.loads(message.data)
        except json.JSONDecodeError:
            return

    def observe(self, request: dict) -> dict:
        if request["target"] == "pressure":
            return self._observe_pressure(request["request_id"])
        return self._observe_temperature(request["request_id"])

    def _spin_until(self, predicate, timeout_s: float) -> bool:
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            rclpy.spin_once(self.node, timeout_sec=0.1)
            if predicate():
                return True
        return False

    def _observe_pressure(self, request_id: str) -> dict:
        self.pressure = {}
        self._spin_until(
            lambda: pressure_is_available(self.pressure), 3.0
        )
        if not pressure_is_available(self.pressure):
            return rejected(
                request_id,
                self.pressure.get(
                    "error_code", "OBSERVER_NOT_DOCKED"
                ),
                "Pressure is available only while the observer is docked.",
            )
        return success(
            request_id,
            "Direct pressure reading acquired through Dora.",
            {
                "available": True,
                "pressure_kpa": self.pressure["value_kpa"],
                "observed_at_s": self.pressure["simulation_time_s"],
            },
        )

    def _observe_temperature(self, request_id: str) -> dict:
        self.observer_state = {}
        self._spin_until(
            lambda: observer_is_docked(self.observer_state), 3.0
        )
        if not observer_is_docked(self.observer_state):
            return rejected(
                request_id,
                "OBSERVER_NOT_DOCKED",
                "Temperature can be observed only at the sensor station.",
            )
        initial_sequence = self.image_sequence
        if not self._spin_until(
            lambda: self.image_sequence > initial_sequence, 5.0
        ):
            return failure(
                request_id,
                "CAMERA_UNAVAILABLE",
                "No fresh observer RGB frame arrived.",
            )
        output_dir = Path(
            os.getenv("PROCESS_OUTPUT_DIR", "/workspace/outputs")
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_id = re.sub(r"[^A-Za-z0-9_.-]", "_", request_id)
        image_path = output_dir / f"{safe_id}-temperature.jpg"
        if not cv2.imwrite(str(image_path), self.image):
            return failure(
                request_id,
                "IMAGE_WRITE_FAILED",
                "The fresh RGB frame could not be saved.",
            )
        try:
            encoded = base64.b64encode(image_path.read_bytes()).decode(
                "ascii"
            )
            response = requests.post(
                os.getenv(
                    "OLLAMA_URL", "http://127.0.0.1:11434"
                ).rstrip("/")
                + "/api/chat",
                json=build_temperature_vlm_request(
                    encoded_image=encoded,
                    model=os.getenv(
                        "OLLAMA_MODEL", "qwen3-vl:8b-instruct"
                    ),
                    prompt=VLM_PROMPT,
                ),
                timeout=120,
            )
            response.raise_for_status()
            payload = response.json()
            observation = parse_temperature_result(
                payload["message"]["content"]
            )
        except Exception as error:
            return failure(
                request_id,
                "VLM_REQUEST_FAILED",
                f"Local VLM observation failed: {error}",
                retryable=True,
                result={"image": str(image_path)},
            )
        return success(
            request_id,
            "Fresh RGB frame analyzed by the local multimodal model.",
            {
                "visible": observation.visible,
                "temperature_c": observation.temperature_c,
                "confidence": observation.confidence,
                "evidence": observation.evidence,
                "image": str(image_path),
                "model": payload.get("model"),
                "inference_duration_ns": payload.get("total_duration"),
            },
        )


def success(request_id: str, message: str, result: dict) -> dict:
    return {
        "request_id": request_id,
        "status": "succeeded",
        "retryable": False,
        "error_code": None,
        "message": message,
        "result": result,
    }


def failure(
    request_id: str,
    code: str,
    message: str,
    *,
    retryable: bool = True,
    result: dict | None = None,
) -> dict:
    return {
        "request_id": request_id,
        "status": "failed",
        "retryable": retryable,
        "error_code": code,
        "message": message,
        "result": result or {},
    }


def rejected(request_id: str, code: str, message: str) -> dict:
    payload = failure(
        request_id, code, message, retryable=False
    )
    payload["status"] = "rejected"
    return payload


def main() -> None:
    rclpy.init()
    runtime = ObservationRuntime()
    dora = Node()
    try:
        for event in dora:
            if event["type"] == "STOP":
                break
            if event["type"] != "INPUT" or event["id"] != "observe":
                continue
            result = runtime.observe(read_json_event(event))
            send_json(
                dora, "result", result, "process.action-result.v1"
            )
    finally:
        runtime.node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
