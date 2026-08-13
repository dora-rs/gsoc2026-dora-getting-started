#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import os
import sys
import threading

import rclpy
from action_msgs.msg import GoalStatus
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node

from mission_state import MissionGate


PREFIX = "DORA_BRIDGE_RESULT "
TARGET_X = float(os.getenv("NAVIGATION_TARGET_X", "0.0"))
TARGET_Y = float(os.getenv("NAVIGATION_TARGET_Y", "0.0"))
TARGET_YAW = float(os.getenv("NAVIGATION_TARGET_YAW", "-0.785398"))


class NavigationClient(Node):
    def __init__(self, gate, lock):
        super().__init__("dora_navigation_action_worker")
        self.gate = gate
        self.lock = lock
        self.client = ActionClient(self, NavigateToPose, "/navigate_to_pose")

    def server_ready(self):
        return self.client.server_is_ready()

    def send_goal(self):
        goal = NavigateToPose.Goal()
        goal.pose.header.frame_id = "map"
        goal.pose.header.stamp = rclpy.time.Time().to_msg()
        goal.pose.pose.position.x = TARGET_X
        goal.pose.pose.position.y = TARGET_Y
        goal.pose.pose.orientation.z = math.sin(TARGET_YAW / 2.0)
        goal.pose.pose.orientation.w = math.cos(TARGET_YAW / 2.0)
        future = self.client.send_goal_async(
            goal, feedback_callback=self.on_feedback
        )
        future.add_done_callback(self.on_goal_response)

    def on_goal_response(self, future):
        goal_handle = future.result()
        with self.lock:
            if not goal_handle.accepted:
                self.gate.complete(False, "Nav2 rejected the navigation goal")
                return
            self.gate.mark_goal_accepted()
        goal_handle.get_result_async().add_done_callback(self.on_result)

    def on_feedback(self, feedback_message):
        with self.lock:
            self.gate.update_feedback(feedback_message.feedback.distance_remaining)

    def on_result(self, future):
        wrapped = future.result()
        succeeded = wrapped.status == GoalStatus.STATUS_SUCCEEDED
        detail = (
            "Nav2 reached the Dora-provided target"
            if succeeded
            else f"Nav2 finished with action status {wrapped.status}"
        )
        with self.lock:
            self.gate.complete(succeeded, detail)


def output_payload(gate):
    payload = gate.as_dict()
    payload["target"] = {
        "frame": "map",
        "x": TARGET_X,
        "y": TARGET_Y,
        "yaw": TARGET_YAW,
    }
    return payload


def emit(result):
    print(PREFIX + json.dumps({"ok": True, "result": result}), flush=True)


def main():
    gate = MissionGate()
    lock = threading.Lock()
    rclpy.init()
    navigation = NavigationClient(gate, lock)
    executor = MultiThreadedExecutor(num_threads=2)
    executor.add_node(navigation)
    thread = threading.Thread(target=executor.spin, daemon=True)
    thread.start()
    try:
        for line in sys.stdin:
            command = json.loads(line)
            if command.get("op") == "finish":
                emit({"finished": True})
                break
            sensors = command.get("sensors")
            should_send = False
            with lock:
                if sensors is not None:
                    gate.update_sensors(sensors)
                should_send = (
                    gate.ready and not gate.goal_sent and navigation.server_ready()
                )
                if should_send:
                    gate.mark_goal_sent()
            if should_send:
                navigation.send_goal()
            with lock:
                emit(output_payload(gate))
    finally:
        executor.shutdown()
        navigation.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
