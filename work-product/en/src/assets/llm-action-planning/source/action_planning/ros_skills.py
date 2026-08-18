from __future__ import annotations

import json
import math
import os
import threading
import time
from pathlib import Path
from typing import Any

import cv2
import rclpy
from cv_bridge import CvBridge
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String

from .model_clients import observe_switch


NAVIGATION_TIMEOUT_S = float(
    os.getenv("ACTION_PLANNING_NAVIGATION_TIMEOUT_S", "180")
)
ARM_ACTION_TIMEOUT_S = float(
    os.getenv("ACTION_PLANNING_ARM_ACTION_TIMEOUT_S", "75")
)
NAMED_ROUTES = {
    ("home", "main_switch"): [
        (-2.35, -1.80),
        (2.55, -1.80),
        (3.15, -1.05),
        (3.15, 0.0),
    ],
    ("main_switch", "home"): [
        (3.15, -1.05),
        (2.55, -1.80),
        (-2.35, -1.80),
        (-2.80, -1.80),
    ],
}
NAMED_POSES = {
    "home": (-2.80, -1.80, 0.0),
    "main_switch": (3.15, 0.0, 0.0),
}


def _yaw_from_quaternion(quaternion):
    return math.atan2(
        2.0
        * (
            quaternion.w * quaternion.z
            + quaternion.x * quaternion.y
        ),
        1.0
        - 2.0
        * (
            quaternion.y * quaternion.y
            + quaternion.z * quaternion.z
        ),
    )


def _angle_error(target, actual):
    return math.atan2(math.sin(target - actual), math.cos(target - actual))


def _clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


class RosSkillRuntime(Node):
    def __init__(self, output_dir: Path):
        super().__init__("action_dora_skill_runtime")
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.bridge = CvBridge()
        self.lock = threading.Lock()
        self.pose = None
        self.image = None
        self.arm_status = None
        self.nav_status = None
        self.switch_state = None
        self.location = "home"
        self.cmd_pub = self.create_publisher(Twist, "/cmd_vel", 10)
        self.arm_pub = self.create_publisher(String, "/action_planning/arm_command", 10)
        self.nav_pub = self.create_publisher(String, "/action_planning/nav_command", 10)
        self.create_subscription(Odometry, "/odom", self._on_odom, 10)
        self.create_subscription(Image, "/camera/image_raw", self._on_image, 10)
        self.create_subscription(
            String, "/action_planning/arm_status", self._on_arm_status, 10
        )
        self.create_subscription(
            String, "/action_planning/nav_status", self._on_nav_status, 10
        )
        self.create_subscription(
            String, "/action_planning/switch_state", self._on_switch_state, 10
        )

    def _on_odom(self, message):
        pose = message.pose.pose
        with self.lock:
            self.pose = (
                float(pose.position.x),
                float(pose.position.y),
                _yaw_from_quaternion(pose.orientation),
            )

    def _on_image(self, message):
        image = self.bridge.imgmsg_to_cv2(message, desired_encoding="bgr8")
        with self.lock:
            self.image = image.copy()

    def _on_arm_status(self, message):
        try:
            status = json.loads(message.data)
        except json.JSONDecodeError:
            return
        with self.lock:
            self.arm_status = status

    def _on_nav_status(self, message):
        try:
            status = json.loads(message.data)
        except json.JSONDecodeError:
            return
        with self.lock:
            self.nav_status = status

    def _on_switch_state(self, message):
        with self.lock:
            self.switch_state = message.data

    def _spin_for(self, duration):
        deadline = time.monotonic() + duration
        while time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=min(0.05, deadline - time.monotonic()))

    def wait_until_ready(self, timeout=15.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)
            with self.lock:
                if self.pose is not None and self.image is not None:
                    return
        raise TimeoutError("ROS sensor bridge did not become ready")

    def execute(self, step_id: str, skill: str, arguments: dict[str, Any]):
        if skill == "navigate_to":
            return self.navigate_to(arguments["location"])
        if skill == "observe_switch":
            return self.observe(step_id)
        if skill == "set_switch_state":
            return self.set_switch_state(
                step_id, arguments["switch_id"], arguments["state"]
            )
        return {"status": "failed", "detail": f"unsupported skill {skill}"}

    def navigate_to(self, target):
        if target not in NAMED_POSES:
            return {"status": "failed", "detail": "unknown named location"}
        request_id = f"navigate-{target}-{int(time.time())}"
        with self.lock:
            self.nav_status = None
        command = {
            "request_id": request_id,
            "action": "navigate_to",
            "location": target,
        }
        self.nav_pub.publish(
            String(data=json.dumps(command, separators=(",", ":")))
        )
        # Dual simulated camera streams can reduce Webots below 0.4x.
        deadline = time.monotonic() + NAVIGATION_TIMEOUT_S
        while time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)
            with self.lock:
                status = self.nav_status
            if not status or status.get("request_id") != request_id:
                continue
            if status["status"] == "succeeded":
                self.location = target
                break
            if status["status"] == "rejected":
                return {"status": "failed", "detail": status["detail"]}
        else:
            return {"status": "failed", "detail": "named navigation timed out"}
        with self.lock:
            pose = self.pose
        return {
            "status": "succeeded",
            "location": target,
            "pose": {
                "x": round(pose[0], 3),
                "y": round(pose[1], 3),
                "yaw": round(pose[2], 3),
            },
        }

    def _drive_to_waypoint(self, target_x, target_y, timeout):
        deadline = time.monotonic() + timeout
        stable_samples = 0
        while time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.02)
            with self.lock:
                pose = self.pose
            if pose is None:
                continue
            x, y, yaw = pose
            dx = target_x - x
            dy = target_y - y
            distance = math.hypot(dx, dy)
            if distance < 0.075:
                stable_samples += 1
                self._stop()
                if stable_samples >= 3:
                    return
                continue
            stable_samples = 0
            desired_yaw = math.atan2(dy, dx)
            heading_error = _angle_error(desired_yaw, yaw)
            command = Twist()
            if abs(heading_error) < 0.30:
                command.linear.x = (
                    _clamp(distance * 0.85, 0.08, 0.42)
                    * max(0.25, math.cos(heading_error))
                )
            command.angular.z = _clamp(1.8 * heading_error, -0.55, 0.55)
            self.cmd_pub.publish(command)
            self._spin_for(0.045)
        raise TimeoutError(
            f"timed out at waypoint ({target_x:.2f}, {target_y:.2f})"
        )

    def _align_heading(self, target_yaw, timeout):
        deadline = time.monotonic() + timeout
        stable_samples = 0
        while time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.03)
            with self.lock:
                pose = self.pose
            error = _angle_error(target_yaw, pose[2])
            if abs(error) < 0.055:
                stable_samples += 1
                self._stop()
                if stable_samples >= 3:
                    return
                continue
            stable_samples = 0
            command = Twist()
            command.angular.z = _clamp(1.6 * error, -0.42, 0.42)
            self.cmd_pub.publish(command)
            self._spin_for(0.045)
        raise TimeoutError("timed out while aligning at named location")

    def _stop(self):
        self.cmd_pub.publish(Twist())

    def observe(self, step_id):
        self._spin_for(0.35)
        with self.lock:
            image = None if self.image is None else self.image.copy()
        if image is None:
            return {"status": "failed", "detail": "camera frame unavailable"}
        image_path = self.output_dir / f"{step_id}.jpg"
        if not cv2.imwrite(str(image_path), image):
            return {"status": "failed", "detail": "failed to save RGB frame"}
        try:
            observation = observe_switch(image_path)
        except Exception as error:
            return {"status": "failed", "detail": f"VLM request failed: {error}"}
        if not observation["visible"] or observation["state"] == "unknown":
            return {
                "status": "failed",
                **observation,
                "image": str(image_path),
            }
        return {
            "status": "succeeded",
            **observation,
            "image": str(image_path),
        }

    def set_switch_state(self, step_id, switch_id, target_state):
        request_id = f"{step_id}-{int(time.time())}"
        with self.lock:
            self.arm_status = None
        command = {
            "request_id": request_id,
            "action": "set_switch_state",
            "switch_id": switch_id,
            "target": target_state,
        }
        self._spin_for(0.4)
        self.arm_pub.publish(
            String(data=json.dumps(command, separators=(",", ":")))
        )
        # Webots may run below 1.0x while GPU rendering and recording are active.
        deadline = time.monotonic() + ARM_ACTION_TIMEOUT_S
        while time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)
            with self.lock:
                status = self.arm_status
            if not status or status.get("request_id") != request_id:
                continue
            if status["status"] == "succeeded":
                return {
                    "status": "succeeded",
                    "state": status["switch_state"],
                    "detail": status["detail"],
                }
            if status["status"] == "rejected":
                return {
                    "status": "failed",
                    "detail": status["detail"],
                }
        return {"status": "failed", "detail": "arm action timed out"}
