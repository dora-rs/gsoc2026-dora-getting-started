#!/usr/bin/env python3
import json
import math
import threading

import pyarrow as pa
import rclpy
from dora import Node as DoraNode
from nav_msgs.msg import OccupancyGrid, Odometry
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan, Range
from tf2_ros import Buffer, TransformListener


def yaw_from_quaternion(q):
    return math.atan2(
        2.0 * (q.w * q.z + q.x * q.y),
        1.0 - 2.0 * (q.y * q.y + q.z * q.z),
    )


class SensorReader(Node):
    def __init__(self):
        super().__init__("week8_dora_sensor_reader")
        self.lock = threading.Lock()
        self.scan_samples = 0
        self.odom_samples = 0
        self.scan = None
        self.odom = None
        self.map = None
        self.sonars = {}
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        self.create_subscription(
            LaserScan, "/scan", self.on_scan, qos_profile_sensor_data
        )
        self.create_subscription(Odometry, "/odom", self.on_odom, 10)
        self.create_subscription(
            OccupancyGrid,
            "/map",
            self.on_map,
            rclpy.qos.QoSProfile(
                depth=1,
                durability=rclpy.qos.DurabilityPolicy.TRANSIENT_LOCAL,
                reliability=rclpy.qos.ReliabilityPolicy.RELIABLE,
            ),
        )
        for topic in (
            "/Tiago_Lite/base_sonar_01_link",
            "/Tiago_Lite/base_sonar_02_link",
            "/Tiago_Lite/base_sonar_03_link",
        ):
            self.create_subscription(
                Range,
                topic,
                lambda message, name=topic: self.on_sonar(name, message),
                qos_profile_sensor_data,
            )

    def on_scan(self, message):
        with self.lock:
            self.scan_samples += 1
            self.scan = message

    def on_odom(self, message):
        with self.lock:
            self.odom_samples += 1
            self.odom = message

    def on_map(self, message):
        with self.lock:
            self.map = message

    def on_sonar(self, name, message):
        with self.lock:
            self.sonars[name.rsplit("/", 1)[-1]] = float(message.range)

    def snapshot(self):
        with self.lock:
            scan = self.scan
            odom = self.odom
            grid = self.map
            sonars = dict(self.sonars)
            scan_samples = self.scan_samples
            odom_samples = self.odom_samples

        finite_ranges = []
        if scan is not None:
            finite_ranges = [
                float(value) for value in scan.ranges if math.isfinite(value)
            ]

        odom_payload = None
        if odom is not None:
            pose = odom.pose.pose
            odom_payload = {
                "x": float(pose.position.x),
                "y": float(pose.position.y),
                "yaw": yaw_from_quaternion(pose.orientation),
            }

        map_payload = {
            "width": 0,
            "height": 0,
            "resolution": None,
            "known_cells": 0,
        }
        if grid is not None:
            map_payload = {
                "width": int(grid.info.width),
                "height": int(grid.info.height),
                "resolution": float(grid.info.resolution),
                "known_cells": sum(value >= 0 for value in grid.data),
            }

        map_pose = None
        try:
            transform = self.tf_buffer.lookup_transform(
                "map", "base_link", rclpy.time.Time()
            )
            translation = transform.transform.translation
            rotation = transform.transform.rotation
            map_pose = {
                "x": float(translation.x),
                "y": float(translation.y),
                "yaw": yaw_from_quaternion(rotation),
            }
        except Exception:
            pass

        return {
            "scan_samples": scan_samples,
            "odom_samples": odom_samples,
            "scan": {
                "frame_id": scan.header.frame_id if scan is not None else None,
                "points": len(scan.ranges) if scan is not None else 0,
                "min_range": min(finite_ranges) if finite_ranges else None,
                "max_range": max(finite_ranges) if finite_ranges else None,
            },
            "odom": odom_payload,
            "map": map_payload,
            "map_pose": map_pose,
            "sonars": sonars,
        }


def main():
    rclpy.init()
    reader = SensorReader()
    executor = MultiThreadedExecutor(num_threads=2)
    executor.add_node(reader)
    thread = threading.Thread(target=executor.spin, daemon=True)
    thread.start()
    dora = DoraNode()

    try:
        for event in dora:
            if event["type"] == "STOP":
                break
            if event["type"] != "INPUT" or event["id"] != "tick":
                continue
            payload = reader.snapshot()
            dora.send_output(
                "status",
                pa.array([json.dumps(payload, separators=(",", ":"))]),
                {"schema": "week8.sensor-status.v1"},
            )
    finally:
        executor.shutdown()
        reader.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
