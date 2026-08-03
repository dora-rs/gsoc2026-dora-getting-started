#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

import rclpy
from dora import Node
from std_msgs.msg import String


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common import send_json


class StateRuntime:
    def __init__(self) -> None:
        self.node = rclpy.create_node("week11_dora_state")
        self.observer = {}
        self.operator = {}
        self.process = {}
        self.node.create_subscription(
            String,
            "/week11/observer/state",
            lambda message: self._store("observer", message),
            10,
        )
        self.node.create_subscription(
            String,
            "/week11/operator/state",
            lambda message: self._store("operator", message),
            10,
        )
        self.node.create_subscription(
            String,
            "/week11/plant/state",
            lambda message: self._store("process", message),
            10,
        )

    def _store(self, target: str, message: String) -> None:
        try:
            setattr(self, target, json.loads(message.data))
        except json.JSONDecodeError:
            return

    def snapshot(self) -> dict:
        return {
            "observer": {
                key: self.observer.get(key)
                for key in (
                    "location",
                    "docked",
                    "navigation_active",
                    "simulation_time_s",
                )
            },
            "operator": {
                key: self.operator.get(key)
                for key in (
                    "location",
                    "at_control",
                    "navigation_active",
                    "arm_active",
                    "switches",
                    "simulation_time_s",
                )
            },
            "process": {
                key: self.process.get(key)
                for key in (
                    "cooling_on",
                    "relief_open",
                    "temperature_safe_min_c",
                    "temperature_safe_max_c",
                    "pressure_safe_min_kpa",
                    "pressure_safe_max_kpa",
                    "temperature_rate_c_per_s",
                    "pressure_rate_kpa_per_s",
                    "control_cycle_count",
                    "phase",
                    "emergency_reason",
                    "agent_action",
                    "simulation_time_s",
                )
            },
        }


def main() -> None:
    rclpy.init()
    runtime = StateRuntime()
    dora = Node()
    try:
        for event in dora:
            if event["type"] == "STOP":
                break
            if event["type"] != "INPUT" or event["id"] != "tick":
                continue
            for _ in range(4):
                rclpy.spin_once(runtime.node, timeout_sec=0.0)
            send_json(
                dora,
                "state",
                runtime.snapshot(),
                "week11.sanitized-state.v1",
            )
    finally:
        runtime.node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
