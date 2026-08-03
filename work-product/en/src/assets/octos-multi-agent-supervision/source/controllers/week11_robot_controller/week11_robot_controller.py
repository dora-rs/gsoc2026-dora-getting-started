#!/usr/bin/env python3
import json
import math
import sys
from pathlib import Path

from controller import Supervisor

import rclpy
from sensor_msgs.msg import Image, LaserScan
from std_msgs.msg import String

from navigation_control import (
    DriveCommand,
    compute_drive_command,
    limit_command,
    mecanum_wheel_speeds,
    ros_yaw_from_webots,
)


TIME_STEP = 32
WHEEL_RADIUS = 0.05
BASE_GEOMETRY = 0.228 + 0.158
MAX_WHEEL_SPEED = 12.0
MAX_LINEAR_ACCELERATION = 0.7
MAX_ANGULAR_ACCELERATION = 1.2
NAV_TIMEOUT_S = 35.0
ARM_PRESS_POSE_SECONDS = 0.7
ARM_SWITCH_EFFECT_SECONDS = 1.5
ARM_RETRACT_SECONDS = 2.2
ARM_ACTION_COMPLETE_SECONDS = 3.0
HOME_ARM = [0.0, 1.57, -2.635, 1.78, 0.0]
READY_ARM = [0.0, 0.0, -0.77, -1.21, 0.0]
PRESS_ARM = [0.0, -0.34, -1.05, -0.85, 0.0]

WORKSPACE = Path(__file__).resolve().parents[2]
LOCATIONS = json.loads(
    (WORKSPACE / "config" / "week11_locations.json").read_text(
        encoding="utf-8"
    )
)


class Week11RobotController:
    def __init__(self) -> None:
        self.robot = Supervisor()
        robot_name = self.robot.getName()
        if "Observer" in robot_name:
            role = "observer"
        else:
            role = "operator"
        self.role = role
        self.node = rclpy.create_node(f"week11_{self.role}_webots_bridge")

        self.wheels = [
            self.robot.getDevice(f"wheel{index}") for index in range(1, 5)
        ]
        self.arm = [
            self.robot.getDevice(f"arm{index}") for index in range(1, 6)
        ]
        self.gps = self.robot.getDevice("gps")
        self.imu = self.robot.getDevice("imu")
        self.lidar = self.robot.getDevice("lidar")
        self.camera = self.robot.getDevice("front_camera")

        self.state_pub = self.node.create_publisher(
            String, f"/week11/{self.role}/state", 10
        )
        self.nav_status_pub = self.node.create_publisher(
            String, f"/week11/{self.role}/nav_status", 10
        )
        self.arm_status_pub = self.node.create_publisher(
            String, f"/week11/{self.role}/arm_status", 10
        )
        self.scan_pub = self.node.create_publisher(
            LaserScan, f"/week11/{self.role}/scan", 10
        )
        if self.role == "observer":
            self.camera_pub = self.node.create_publisher(
                Image, "/week11/observer/camera/image_raw", 10
            )
        else:
            self.camera_pub = None
        self.switch_pub = self.node.create_publisher(
            String, "/week11/operator/switch_event", 10
        )
        self.node.create_subscription(
            String,
            f"/week11/{self.role}/nav_command",
            self.on_nav_command,
            10,
        )
        self.node.create_subscription(
            String,
            f"/week11/{self.role}/arm_command",
            self.on_arm_command,
            10,
        )
        self.node.create_subscription(
            String, f"/week11/{self.role}/stop", self.on_stop, 10
        )

        self.home_key = f"{self.role}_home"
        self.station_key = (
            "observer_station"
            if self.role == "observer"
            else "control_station"
        )
        self.location = "home"
        self.nav_task = None
        self.arm_task = None
        self.drive_command = DriveCommand(0.0, 0.0, 0.0)
        self.switches = {"cooling": False, "relief": False}
        self._configure_devices()
        print(
            json.dumps(
                {
                    "event": "WEEK11_ROBOT_READY",
                    "role": self.role,
                    "robot": robot_name,
                },
                separators=(",", ":"),
            ),
            flush=True,
        )

    def _configure_devices(self) -> None:
        for wheel in self.wheels:
            wheel.setPosition(float("inf"))
            wheel.setVelocity(0.0)
        for motor, target in zip(self.arm, HOME_ARM):
            motor.setVelocity(0.75)
            motor.setPosition(target)
        for finger_name in ("finger::left", "finger::right"):
            self.robot.getDevice(finger_name).setPosition(0.012)
        for device in (self.gps, self.imu, self.lidar):
            device.enable(TIME_STEP)
        if self.role == "observer":
            self.camera.enable(TIME_STEP)

    def _pose(self) -> tuple[float, float, float]:
        x, y, _ = self.gps.getValues()
        yaw = ros_yaw_from_webots(self.imu.getRollPitchYaw()[2])
        return x, y, yaw

    def _at_station(self) -> bool:
        x, y, yaw = self._pose()
        target = LOCATIONS[self.station_key]
        heading_error = math.atan2(
            math.sin(target["yaw"] - yaw),
            math.cos(target["yaw"] - yaw),
        )
        return (
            math.hypot(target["x"] - x, target["y"] - y) <= 0.14
            and abs(heading_error) <= math.radians(10)
        )

    def on_nav_command(self, message: String) -> None:
        try:
            command = json.loads(message.data)
        except json.JSONDecodeError:
            self._publish_nav("rejected", "command is not valid JSON")
            return
        target_name = command.get("location")
        target_key = {
            "home": self.home_key,
            "station": self.station_key,
            self.station_key: self.station_key,
        }.get(target_name)
        if command.get("action") != "navigate_to" or target_key is None:
            self._publish_nav("rejected", "unknown named navigation action")
            return
        if self.nav_task is not None or self.arm_task is not None:
            self._publish_nav("rejected", "robot is busy")
            return
        self.nav_task = {
            "request_id": command.get("request_id", "navigation"),
            "target_name": "home" if target_key == self.home_key else "station",
            "target_key": target_key,
            "started": self.robot.getTime(),
        }
        self._publish_nav(
            "running", f"moving {self.role} to {self.nav_task['target_name']}"
        )

    def on_arm_command(self, message: String) -> None:
        if self.role != "operator":
            self._publish_arm("rejected", "observer has no switch tool")
            return
        try:
            command = json.loads(message.data)
        except json.JSONDecodeError:
            self._publish_arm("rejected", "command is not valid JSON")
            return
        switch_name = command.get("switch")
        enabled = command.get("enabled")
        if (
            command.get("action") != "set_switch"
            or switch_name not in {"cooling", "relief"}
            or not isinstance(enabled, bool)
        ):
            self._publish_arm("rejected", "unknown named switch action")
            return
        if self.nav_task is not None or self.arm_task is not None:
            self._publish_arm("rejected", "robot is busy")
            return
        if self.location != "station" or not self._at_station():
            self._publish_arm("rejected", "operator is not at control station")
            return
        base_angle = -0.34 if switch_name == "cooling" else 0.34
        ready = [base_angle, *READY_ARM[1:]]
        press = [base_angle, *PRESS_ARM[1:]]
        self.arm_task = {
            "request_id": command.get("request_id", "switch-action"),
            "switch": switch_name,
            "enabled": enabled,
            "started": self.robot.getTime(),
            "phase": "ready",
            "event_sent": False,
            "ready": ready,
            "press": press,
        }
        self._set_arm(ready)
        self._publish_arm(
            "running", f"approaching verified {switch_name} switch pose"
        )

    def on_stop(self, message: String) -> None:
        self.nav_task = None
        self.arm_task = None
        self.drive_command = DriveCommand(0.0, 0.0, 0.0)
        self._set_arm(HOME_ARM)
        self._publish_nav("cancelled", message.data or "stop requested")
        self._publish_arm("cancelled", message.data or "stop requested")

    def _set_arm(self, pose: list[float]) -> None:
        for motor, target in zip(self.arm, pose):
            motor.setPosition(target)

    def _publish_nav(self, status: str, detail: str) -> None:
        payload = {
            "status": status,
            "detail": detail,
            "role": self.role,
            "location": self.location,
        }
        if self.nav_task:
            payload["request_id"] = self.nav_task["request_id"]
        self.nav_status_pub.publish(String(data=json.dumps(payload)))
        print(json.dumps({"event": "NAV_STATUS", **payload}), flush=True)

    def _publish_arm(self, status: str, detail: str) -> None:
        payload = {"status": status, "detail": detail, "role": self.role}
        if self.arm_task:
            payload["request_id"] = self.arm_task["request_id"]
            payload["switch"] = self.arm_task["switch"]
        self.arm_status_pub.publish(String(data=json.dumps(payload)))
        print(json.dumps({"event": "ARM_STATUS", **payload}), flush=True)

    def _update_navigation(self) -> None:
        if self.nav_task is None:
            self.drive_command = DriveCommand(0.0, 0.0, 0.0)
            return
        if self.robot.getTime() - self.nav_task["started"] > NAV_TIMEOUT_S:
            self.drive_command = DriveCommand(0.0, 0.0, 0.0)
            self._publish_nav("failed", "named route timed out")
            self.nav_task = None
            return
        target = LOCATIONS[self.nav_task["target_key"]]
        x, y, yaw = self._pose()
        desired = compute_drive_command(
            current_x=x,
            current_y=y,
            current_yaw=yaw,
            target_x=target["x"],
            target_y=target["y"],
            target_yaw=target["yaw"],
        )
        if desired.reached:
            self.location = self.nav_task["target_name"]
            self.drive_command = DriveCommand(0.0, 0.0, 0.0)
            self._publish_nav(
                "succeeded", f"{self.role} reached {self.location}"
            )
            self.nav_task = None
            return
        self.drive_command = limit_command(
            self.drive_command,
            desired,
            linear_delta=MAX_LINEAR_ACCELERATION * TIME_STEP / 1000.0,
            angular_delta=MAX_ANGULAR_ACCELERATION * TIME_STEP / 1000.0,
        )

    def _update_arm(self) -> None:
        if self.arm_task is None:
            return
        elapsed = self.robot.getTime() - self.arm_task["started"]
        if (
            elapsed >= ARM_PRESS_POSE_SECONDS
            and self.arm_task["phase"] == "ready"
        ):
            self._set_arm(self.arm_task["press"])
            self.arm_task["phase"] = "press"
            self._publish_arm(
                "running", f"pressing {self.arm_task['switch']} switch"
            )
        if (
            elapsed >= ARM_SWITCH_EFFECT_SECONDS
            and not self.arm_task["event_sent"]
        ):
            switch_name = self.arm_task["switch"]
            enabled = self.arm_task["enabled"]
            self.switches[switch_name] = enabled
            event = {
                "switch": switch_name,
                "enabled": enabled,
                "request_id": self.arm_task["request_id"],
                "observed_at_s": self.robot.getTime(),
            }
            self.switch_pub.publish(String(data=json.dumps(event)))
            self.arm_task["event_sent"] = True
            self.arm_task["phase"] = "retract"
            self._set_arm(self.arm_task["ready"])
            self._publish_arm(
                "running", f"{switch_name} changed; retracting arm"
            )
        if (
            elapsed >= ARM_RETRACT_SECONDS
            and self.arm_task["phase"] == "retract"
        ):
            self._set_arm(HOME_ARM)
            self.arm_task["phase"] = "home"
        if (
            elapsed >= ARM_ACTION_COMPLETE_SECONDS
            and self.arm_task["phase"] == "home"
        ):
            self._publish_arm(
                "succeeded",
                f"{self.arm_task['switch']} switch action complete",
            )
            self.arm_task = None

    def _drive(self) -> None:
        speeds = mecanum_wheel_speeds(
            self.drive_command,
            wheel_radius=WHEEL_RADIUS,
            geometry=BASE_GEOMETRY,
            max_wheel_speed=MAX_WHEEL_SPEED,
        )
        for motor, speed in zip(self.wheels, speeds):
            motor.setVelocity(speed)

    def _publish_state(self) -> None:
        x, y, yaw = self._pose()
        payload = {
            "role": self.role,
            "location": self.location,
            "pose": {"x": x, "y": y, "yaw": yaw},
            "navigation_active": self.nav_task is not None,
            "arm_active": self.arm_task is not None,
            "docked": self.role == "observer" and self._at_station(),
            "at_control": self.role == "operator" and self._at_station(),
            "switches": self.switches if self.role == "operator" else {},
            "simulation_time_s": self.robot.getTime(),
        }
        self.state_pub.publish(String(data=json.dumps(payload)))

    def _publish_scan(self) -> None:
        ranges = list(self.lidar.getRangeImage())
        message = LaserScan()
        message.header.stamp = self.node.get_clock().now().to_msg()
        message.header.frame_id = f"{self.role}_base_link"
        message.angle_min = -math.pi
        message.angle_max = math.pi
        message.angle_increment = 2.0 * math.pi / len(ranges)
        message.range_min = self.lidar.getMinRange()
        message.range_max = self.lidar.getMaxRange()
        message.ranges = ranges
        self.scan_pub.publish(message)

    def _publish_camera(self) -> None:
        if self.camera_pub is None:
            return
        message = Image()
        message.header.stamp = self.node.get_clock().now().to_msg()
        message.header.frame_id = "observer_front_camera"
        message.height = self.camera.getHeight()
        message.width = self.camera.getWidth()
        message.encoding = "bgra8"
        message.step = message.width * 4
        message.data = self.camera.getImage()
        self.camera_pub.publish(message)

    def run(self) -> None:
        counter = 0
        while self.robot.step(TIME_STEP) != -1:
            rclpy.spin_once(self.node, timeout_sec=0.0)
            self._update_navigation()
            self._update_arm()
            self._drive()
            counter += 1
            if counter % 4 == 0:
                self._publish_camera()
            if counter % 8 == 0:
                self._publish_scan()
            if counter % 8 == 0:
                self._publish_state()
        for wheel in self.wheels:
            wheel.setVelocity(0.0)
        self.node.destroy_node()


def main() -> None:
    rclpy.init(args=sys.argv)
    controller = Week11RobotController()
    try:
        controller.run()
    finally:
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
