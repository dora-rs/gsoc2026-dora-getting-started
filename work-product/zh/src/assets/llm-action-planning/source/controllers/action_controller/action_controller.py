#!/usr/bin/env python3
import json
import math
import os
import sys
from pathlib import Path

from controller import Supervisor

import rclpy
from geometry_msgs.msg import Quaternion, TransformStamped, Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Image, LaserScan
from std_msgs.msg import String
from tf2_ros import StaticTransformBroadcaster, TransformBroadcaster

from navigation_control import (
    DriveCommand,
    compute_drive_command,
    limit_command,
    mecanum_wheel_speeds,
    pose_is_within_tolerance,
    ros_yaw_from_webots,
)


TIME_STEP = 32
WHEEL_RADIUS = 0.05
BASE_GEOMETRY = 0.228 + 0.158
MAX_WHEEL_SPEED = 12.0
MAX_LINEAR_ACCELERATION = 0.65
MAX_ANGULAR_ACCELERATION = 1.2
NAV_SEGMENT_TIMEOUT = 30.0
ARM_SETTLE_TOLERANCE = 0.01
ARM_TASK_TIMEOUT = 14.0
HOME_ARM = [0.0, 1.57, -2.635, 1.78, 0.0]
READY_ARM = [0.0, 0.0, -0.77, -1.21, 0.0]
PUSH_ARM = [0.0, -0.34, -1.05, -0.85, 0.0]
NAV_ROUTES = {
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


def quaternion_from_yaw(yaw):
    return Quaternion(z=math.sin(yaw / 2.0), w=math.cos(yaw / 2.0))


class ActionController:
    def __init__(self):
        self.robot = Supervisor()
        self.node = rclpy.create_node("action_webots_bridge")
        self.wheels = [self.robot.getDevice(f"wheel{i}") for i in range(1, 5)]
        self.arm = [self.robot.getDevice(f"arm{i}") for i in range(1, 6)]
        self.arm_sensors = [
            self.robot.getDevice(f"arm{i}sensor") for i in range(1, 6)
        ]
        self.fingers = [
            self.robot.getDevice("finger::left"),
            self.robot.getDevice("finger::right"),
        ]
        self.gps = self.robot.getDevice("gps")
        self.imu = self.robot.getDevice("imu")
        self.lidar = self.robot.getDevice("lidar")
        self.camera = self.robot.getDevice("front_camera")
        self.camera_node = self.robot.getFromDevice(self.camera._tag)
        self.switch_lever = self.robot.getFromDef("SWITCH_LEVER")
        self.switch_led = self.robot.getFromDef("SWITCH_LED_APPEARANCE")
        self.self_node = self.robot.getSelf()

        self.odom_pub = self.node.create_publisher(Odometry, "/odom", 10)
        self.scan_pub = self.node.create_publisher(LaserScan, "/scan", 10)
        self.camera_pub = self.node.create_publisher(Image, "/camera/image_raw", 10)
        self.arm_status_pub = self.node.create_publisher(String, "/action_planning/arm_status", 10)
        self.nav_status_pub = self.node.create_publisher(String, "/action_planning/nav_status", 10)
        self.switch_pub = self.node.create_publisher(String, "/action_planning/switch_state", 10)
        self.tf_pub = TransformBroadcaster(self.node)
        self.static_tf_pub = StaticTransformBroadcaster(self.node)
        self.node.create_subscription(Twist, "/cmd_vel", self.on_cmd_vel, 10)
        self.node.create_subscription(
            String, "/action_planning/arm_command", self.on_arm_command, 10
        )
        self.node.create_subscription(
            String, "/action_planning/nav_command", self.on_nav_command, 10
        )

        self.cmd_vel = Twist()
        self.last_cmd_time = self.robot.getTime()
        self.last_pose = None
        self.last_pose_time = None
        self.arm_task = None
        self.nav_task = None
        self.location = "home"
        self.switch_state = os.getenv("ACTION_PLANNING_SWITCH_INITIAL", "on").lower()
        self.nav_drive_command = DriveCommand(0.0, 0.0, 0.0)
        self.diagnostic_path = os.getenv("ACTION_PLANNING_POSE_DIAGNOSTICS")
        self.diagnostic_file = None
        self.autostart_target = os.getenv("ACTION_PLANNING_AUTOSTART_NAV")
        self.autostart_pending = self.autostart_target in {"home", "main_switch"}
        self.quit_after_navigation = os.getenv("ACTION_PLANNING_QUIT_AFTER_NAV") == "1"
        diagnostic_twist = os.getenv("ACTION_PLANNING_DIAGNOSTIC_TWIST")
        self.diagnostic_twist = (
            tuple(float(value) for value in diagnostic_twist.split(","))
            if diagnostic_twist
            else None
        )
        if self.diagnostic_twist is not None and len(self.diagnostic_twist) != 3:
            raise ValueError("ACTION_PLANNING_DIAGNOSTIC_TWIST requires vx,vy,omega")
        self.diagnostic_quit_time = float(
            os.getenv("ACTION_PLANNING_DIAGNOSTIC_QUIT_TIME", "0")
        )
        if self.switch_state not in {"on", "off"}:
            self.switch_state = "on"

        self._configure_devices()
        self._set_switch_visuals()
        self._publish_static_tf()
        self._report_devices()

    def _configure_devices(self):
        for wheel in self.wheels:
            wheel.setPosition(float("inf"))
            wheel.setVelocity(0.0)
        for motor, target in zip(self.arm, HOME_ARM):
            motor.setVelocity(0.65)
            motor.setPosition(target)
        for sensor in self.arm_sensors:
            sensor.enable(TIME_STEP)
        for finger in self.fingers:
            finger.setPosition(0.012)
        for device in (self.gps, self.imu, self.lidar, self.camera):
            device.enable(TIME_STEP)
        rotation_override = os.getenv("ACTION_PLANNING_CAMERA_ROTATION")
        if rotation_override:
            rotation = [float(value) for value in rotation_override.split(",")]
            if len(rotation) != 4:
                raise ValueError("ACTION_PLANNING_CAMERA_ROTATION requires four values")
            self.camera_node.getField("rotation").setSFRotation(rotation)

    def _report_devices(self):
        report = {
            "event": "DEVICE_REPORT",
            "devices": {
                name: self.robot.getDevice(name) is not None
                for name in (
                    "wheel1",
                    "wheel2",
                    "wheel3",
                    "wheel4",
                    "arm1",
                    "arm2",
                    "arm3",
                    "arm4",
                    "arm5",
                    "finger::left",
                    "finger::right",
                    "gps",
                    "imu",
                    "lidar",
                    "front_camera",
                )
            },
            "switch_lever": self.switch_lever is not None,
            "switch_led": self.switch_led is not None,
            "initial_switch": self.switch_state,
        }
        print(json.dumps(report, separators=(",", ":")), flush=True)

    def _publish_static_tf(self):
        transform = TransformStamped()
        transform.header.stamp = self.node.get_clock().now().to_msg()
        transform.header.frame_id = "map"
        transform.child_frame_id = "odom"
        transform.transform.rotation.w = 1.0
        self.static_tf_pub.sendTransform(transform)

    def on_cmd_vel(self, message):
        self.cmd_vel = message
        self.last_cmd_time = self.robot.getTime()

    def on_arm_command(self, message):
        try:
            command = json.loads(message.data)
        except json.JSONDecodeError:
            self._publish_arm_status("rejected", "arm command is not valid JSON")
            return
        if command.get("action") != "set_switch_state":
            self._publish_arm_status("rejected", "unsupported arm action")
            return
        if command.get("target") not in {"on", "off"}:
            self._publish_arm_status("rejected", "target must be on or off")
            return
        if self.arm_task is not None:
            self._publish_arm_status("rejected", "arm is already busy")
            return
        distance, heading_error = self._switch_pose_error()
        if distance > 0.72 or heading_error > 0.38:
            self._publish_arm_status(
                "rejected",
                f"robot is outside switch workspace: distance={distance:.2f}, "
                f"heading_error={heading_error:.2f}",
            )
            return
        self.arm_task = {
            "request_id": command.get("request_id", "switch-action"),
            "target": command["target"],
            "started": self.robot.getTime(),
            "phase": "ready",
            "toggled": False,
        }
        self._set_arm_pose(READY_ARM)
        self._publish_arm_status("running", "moving arm to switch-ready pose")

    def on_nav_command(self, message):
        try:
            command = json.loads(message.data)
        except json.JSONDecodeError:
            self._publish_nav_status("rejected", "navigation command is not valid JSON")
            return
        if command.get("action") != "navigate_to":
            self._publish_nav_status("rejected", "unsupported navigation action")
            return
        target = command.get("location")
        if target not in {"home", "main_switch"}:
            self._publish_nav_status("rejected", "unknown named location")
            return
        if self.nav_task is not None:
            self._publish_nav_status("rejected", "navigation is already busy")
            return
        route = (
            [(self.gps.getValues()[0], self.gps.getValues()[1])]
            if target == self.location
            else NAV_ROUTES.get((self.location, target))
        )
        if route is None:
            self._publish_nav_status("rejected", "no validated named route")
            return
        self.nav_task = {
            "request_id": command.get("request_id", "navigation"),
            "target": target,
            "points": route,
            "segment": 0,
            "segment_started": None,
            "waiting_for_arm": not self._arm_at_pose(HOME_ARM),
        }
        self.nav_drive_command = DriveCommand(0.0, 0.0, 0.0)
        detail = (
            "waiting for arm to settle at home pose"
            if self.nav_task["waiting_for_arm"]
            else f"following validated route to {target}"
        )
        if not self.nav_task["waiting_for_arm"]:
            self.nav_task["segment_started"] = self.robot.getTime()
        self._publish_nav_status("running", detail)

    def _switch_pose_error(self):
        x, y, _ = self.gps.getValues()
        yaw = ros_yaw_from_webots(self.imu.getRollPitchYaw()[2])
        return math.hypot(3.15 - x, -y), abs(math.atan2(math.sin(yaw), math.cos(yaw)))

    def _set_arm_pose(self, pose):
        for motor, target in zip(self.arm, pose):
            motor.setPosition(target)

    def _arm_at_pose(self, pose):
        return pose_is_within_tolerance(
            [sensor.getValue() for sensor in self.arm_sensors],
            pose,
            tolerance=ARM_SETTLE_TOLERANCE,
        )

    def _set_switch_visuals(self):
        is_on = self.switch_state == "on"
        angle = -0.55 if is_on else 0.95
        color = [0.05, 0.9, 0.25] if is_on else [0.01, 0.01, 0.01]
        self.switch_lever.getField("rotation").setSFRotation([0.0, 1.0, 0.0, angle])
        self.switch_led.getField("baseColor").setSFColor(color)
        self.switch_led.getField("emissiveColor").setSFColor(color)

    def _publish_arm_status(self, status, detail):
        payload = {
            "status": status,
            "detail": detail,
            "switch_state": self.switch_state,
        }
        if self.arm_task:
            payload["request_id"] = self.arm_task["request_id"]
        self.arm_status_pub.publish(String(data=json.dumps(payload, separators=(",", ":"))))
        print(json.dumps({"event": "ARM_STATUS", **payload}, separators=(",", ":")), flush=True)

    def _publish_nav_status(self, status, detail):
        payload = {
            "status": status,
            "detail": detail,
            "location": self.location,
        }
        if self.nav_task:
            payload["request_id"] = self.nav_task["request_id"]
        self.nav_status_pub.publish(String(data=json.dumps(payload, separators=(",", ":"))))
        print(json.dumps({"event": "NAV_STATUS", **payload}, separators=(",", ":")), flush=True)

    def _update_arm_task(self):
        if self.arm_task is None:
            return
        elapsed = self.robot.getTime() - self.arm_task["started"]
        if elapsed >= 1.8 and self.arm_task["phase"] == "ready":
            self._set_arm_pose(PUSH_ARM)
            self.arm_task["phase"] = "push"
            self._publish_arm_status("running", "executing validated switch trajectory")
        if elapsed >= 3.2 and not self.arm_task["toggled"]:
            self.switch_state = self.arm_task["target"]
            self._set_switch_visuals()
            self.arm_task["toggled"] = True
            self._publish_arm_status("running", "switch contact accepted")
        if elapsed >= 4.4 and self.arm_task["phase"] == "push":
            self._set_arm_pose(READY_ARM)
            self.arm_task["phase"] = "retract"
        if elapsed >= 5.8 and self.arm_task["phase"] == "retract":
            self._set_arm_pose(HOME_ARM)
            self.arm_task["phase"] = "home"
            self._publish_arm_status("running", "returning arm to home pose")
        if (
            elapsed >= 8.0
            and self.arm_task["phase"] == "home"
            and self._arm_at_pose(HOME_ARM)
        ):
            self._publish_arm_status("succeeded", "preset switch action completed")
            self.arm_task = None
        elif elapsed >= ARM_TASK_TIMEOUT:
            self._publish_arm_status("failed", "arm did not settle at home pose")
            self.arm_task = None

    def _update_nav_task(self):
        if self.nav_task is None:
            return
        if self.nav_task["waiting_for_arm"]:
            self.nav_drive_command = DriveCommand(0.0, 0.0, 0.0)
            if self._arm_at_pose(HOME_ARM):
                self.nav_task["waiting_for_arm"] = False
                self.nav_task["segment_started"] = self.robot.getTime()
                self._publish_nav_status(
                    "running",
                    f"following validated route to {self.nav_task['target']}",
                )
            return
        points = self.nav_task["points"]
        segment = self.nav_task["segment"]
        if segment >= len(points):
            target = self.nav_task["target"]
            self.location = target
            self.nav_drive_command = DriveCommand(0.0, 0.0, 0.0)
            self._publish_nav_status("succeeded", f"reached named location {target}")
            self.nav_task = None
            return
        if self.robot.getTime() - self.nav_task["segment_started"] > NAV_SEGMENT_TIMEOUT:
            self.nav_drive_command = DriveCommand(0.0, 0.0, 0.0)
            self._publish_nav_status(
                "failed",
                f"timed out while approaching waypoint {segment + 1}",
            )
            self.nav_task = None
            return

        x, y, _ = self.gps.getValues()
        yaw = ros_yaw_from_webots(self.imu.getRollPitchYaw()[2])
        target_x, target_y = points[segment]
        target_command = compute_drive_command(
            current_x=x,
            current_y=y,
            current_yaw=yaw,
            target_x=target_x,
            target_y=target_y,
        )
        if target_command.reached:
            self.nav_task["segment"] += 1
            self.nav_task["segment_started"] = self.robot.getTime()
            self.nav_drive_command = DriveCommand(0.0, 0.0, 0.0)
            return
        dt = TIME_STEP / 1000.0
        self.nav_drive_command = limit_command(
            self.nav_drive_command,
            target_command,
            linear_delta=MAX_LINEAR_ACCELERATION * dt,
            angular_delta=MAX_ANGULAR_ACCELERATION * dt,
        )

    def _drive_wheels(self):
        if self.nav_task is not None:
            command = self.nav_drive_command
        else:
            if self.robot.getTime() - self.last_cmd_time > 0.35:
                command = DriveCommand(0.0, 0.0, 0.0)
            else:
                command = DriveCommand(
                    self.cmd_vel.linear.x,
                    self.cmd_vel.linear.y,
                    self.cmd_vel.angular.z,
                )
        speeds = mecanum_wheel_speeds(
            command,
            wheel_radius=WHEEL_RADIUS,
            geometry=BASE_GEOMETRY,
            max_wheel_speed=MAX_WHEEL_SPEED,
        )
        for motor, speed in zip(self.wheels, speeds):
            motor.setVelocity(speed)

    def _current_velocity(self, x, y, yaw):
        now = self.robot.getTime()
        if self.last_pose is None or now == self.last_pose_time:
            velocity = (0.0, 0.0, 0.0)
        else:
            dt = now - self.last_pose_time
            previous_x, previous_y, previous_yaw = self.last_pose
            world_vx = (x - previous_x) / dt
            world_vy = (y - previous_y) / dt
            velocity = (
                math.cos(yaw) * world_vx + math.sin(yaw) * world_vy,
                -math.sin(yaw) * world_vx + math.cos(yaw) * world_vy,
                math.atan2(
                    math.sin(yaw - previous_yaw), math.cos(yaw - previous_yaw)
                )
                / dt,
            )
        self.last_pose = (x, y, yaw)
        self.last_pose_time = now
        return velocity

    def _publish_odometry(self):
        x, y, _ = self.gps.getValues()
        yaw = ros_yaw_from_webots(self.imu.getRollPitchYaw()[2])
        vx, vy, omega = self._current_velocity(x, y, yaw)
        stamp = self.node.get_clock().now().to_msg()
        orientation = quaternion_from_yaw(yaw)

        odom = Odometry()
        odom.header.stamp = stamp
        odom.header.frame_id = "odom"
        odom.child_frame_id = "base_link"
        odom.pose.pose.position.x = x
        odom.pose.pose.position.y = y
        odom.pose.pose.orientation = orientation
        odom.twist.twist.linear.x = vx
        odom.twist.twist.linear.y = vy
        odom.twist.twist.angular.z = omega
        self.odom_pub.publish(odom)

        transform = TransformStamped()
        transform.header.stamp = stamp
        transform.header.frame_id = "odom"
        transform.child_frame_id = "base_link"
        transform.transform.translation.x = x
        transform.transform.translation.y = y
        transform.transform.rotation = orientation
        self.tf_pub.sendTransform(transform)

    def _publish_scan(self):
        ranges = list(self.lidar.getRangeImage())
        message = LaserScan()
        message.header.stamp = self.node.get_clock().now().to_msg()
        message.header.frame_id = "base_link"
        message.angle_min = -math.pi
        message.angle_max = math.pi
        message.angle_increment = 2.0 * math.pi / len(ranges)
        message.scan_time = TIME_STEP / 1000.0
        message.time_increment = message.scan_time / len(ranges)
        message.range_min = self.lidar.getMinRange()
        message.range_max = self.lidar.getMaxRange()
        message.ranges = ranges
        self.scan_pub.publish(message)

    def _publish_camera(self):
        message = Image()
        message.header.stamp = self.node.get_clock().now().to_msg()
        message.header.frame_id = "front_camera"
        message.height = self.camera.getHeight()
        message.width = self.camera.getWidth()
        message.encoding = "bgra8"
        message.is_bigendian = 0
        message.step = message.width * 4
        message.data = self.camera.getImage()
        self.camera_pub.publish(message)

    def _write_pose_diagnostics(self):
        if not self.diagnostic_path:
            return
        if self.diagnostic_file is None:
            path = Path(self.diagnostic_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            self.diagnostic_file = path.open("w", encoding="utf-8")
            columns = [
                "time_s",
                "nav_active",
                "base_x",
                "base_y",
                "base_z",
                "roll",
                "pitch",
                "yaw",
                "camera_relative_pose",
                *[f"arm{i}" for i in range(1, 6)],
            ]
            self.diagnostic_file.write(",".join(columns) + "\n")
        base = self.self_node.getPosition()
        roll, pitch, webots_yaw = self.imu.getRollPitchYaw()
        yaw = ros_yaw_from_webots(webots_yaw)
        camera_pose = self.camera_node.getPose(self.self_node)
        values = [
            f"{self.robot.getTime():.6f}",
            "1" if self.nav_task is not None else "0",
            *(f"{value:.9f}" for value in base),
            f"{roll:.9f}",
            f"{pitch:.9f}",
            f"{yaw:.9f}",
            '"' + " ".join(f"{value:.9f}" for value in camera_pose) + '"',
            *(f"{sensor.getValue():.9f}" for sensor in self.arm_sensors),
        ]
        self.diagnostic_file.write(",".join(values) + "\n")
        self.diagnostic_file.flush()

    def run(self):
        publish_counter = 0
        while self.robot.step(TIME_STEP) != -1:
            rclpy.spin_once(self.node, timeout_sec=0.0)
            if self.autostart_pending and self.robot.getTime() >= 3.0:
                command = {
                    "action": "navigate_to",
                    "location": self.autostart_target,
                    "request_id": "diagnostic-navigation",
                }
                self.on_nav_command(
                    String(data=json.dumps(command, separators=(",", ":")))
                )
                self.autostart_pending = False
            if self.diagnostic_twist is not None and self.robot.getTime() >= 3.0:
                self.cmd_vel.linear.x = self.diagnostic_twist[0]
                self.cmd_vel.linear.y = self.diagnostic_twist[1]
                self.cmd_vel.angular.z = self.diagnostic_twist[2]
                self.last_cmd_time = self.robot.getTime()
            self._update_nav_task()
            self._drive_wheels()
            self._update_arm_task()
            self._publish_odometry()
            self._publish_scan()
            self._publish_camera()
            self._write_pose_diagnostics()
            publish_counter += 1
            if publish_counter % 8 == 0:
                self.switch_pub.publish(String(data=self.switch_state))
            if (
                self.quit_after_navigation
                and not self.autostart_pending
                and self.nav_task is None
                and self.robot.getTime() > 4.0
            ):
                self.robot.simulationQuit(0)
            if (
                self.diagnostic_quit_time > 0.0
                and self.robot.getTime() >= self.diagnostic_quit_time
            ):
                self.robot.simulationQuit(0)
        for wheel in self.wheels:
            wheel.setVelocity(0.0)
        if self.diagnostic_file is not None:
            self.diagnostic_file.close()
        self.node.destroy_node()


def main():
    rclpy.init(args=sys.argv)
    controller = ActionController()
    try:
        controller.run()
    finally:
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
