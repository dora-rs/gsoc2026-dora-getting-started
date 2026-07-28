#!/usr/bin/env python3
import math
import sys
import time

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from sensor_msgs.msg import LaserScan


def finite_min(values, default):
    valid = [value for value in values if math.isfinite(value)]
    return min(valid) if valid else default


class LidarExplorer(Node):
    def __init__(self, duration):
        super().__init__("week8_lidar_explorer")
        self.duration = duration
        self.started_at = time.monotonic()
        self.scan = None
        self.publisher = self.create_publisher(Twist, "/cmd_vel", 10)
        self.create_subscription(LaserScan, "/scan", self.on_scan, 10)
        self.create_timer(0.1, self.on_timer)

    def on_scan(self, scan):
        self.scan = scan

    def sector_min(self, start_degrees, end_degrees):
        if self.scan is None:
            return 0.0

        start = math.radians(start_degrees)
        end = math.radians(end_degrees)
        values = []
        for index, value in enumerate(self.scan.ranges):
            angle = self.scan.angle_min + index * self.scan.angle_increment
            if start <= angle <= end:
                values.append(value)
        return finite_min(values, self.scan.range_max)

    def on_timer(self):
        command = Twist()
        if self.scan is None:
            self.publisher.publish(command)
            return

        elapsed = time.monotonic() - self.started_at
        if elapsed >= self.duration:
            self.publisher.publish(command)
            self.get_logger().info("Exploration complete")
            raise SystemExit(0)

        front = self.sector_min(-22, 22)
        left = self.sector_min(25, 95)
        right = self.sector_min(-95, -25)

        if front < 0.8:
            command.angular.z = 0.5 if left >= right else -0.5
        else:
            command.linear.x = 0.24
            openness_error = max(-2.0, min(2.0, left - right))
            command.angular.z = 0.10 * openness_error

        self.publisher.publish(command)


def main():
    duration = float(sys.argv[1]) if len(sys.argv) > 1 else 75.0
    rclpy.init()
    node = LidarExplorer(duration)
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        node.publisher.publish(Twist())
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
