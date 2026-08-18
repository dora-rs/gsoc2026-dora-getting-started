#!/usr/bin/env python3
import sys

from controller import Robot

import rclpy
from sensor_msgs.msg import Image


TIME_STEP = 32


def main():
    rclpy.init(args=sys.argv)
    robot = Robot()
    node = rclpy.create_node("action_scene_camera_bridge")
    camera = robot.getDevice("scene_camera")
    camera.enable(TIME_STEP)
    publisher = node.create_publisher(Image, "/scene_camera/image_raw", 10)
    try:
        while robot.step(TIME_STEP) != -1:
            message = Image()
            message.header.stamp = node.get_clock().now().to_msg()
            message.header.frame_id = "fixed_scene_camera"
            message.height = camera.getHeight()
            message.width = camera.getWidth()
            message.encoding = "bgra8"
            message.is_bigendian = 0
            message.step = message.width * 4
            message.data = camera.getImage()
            publisher.publish(message)
            rclpy.spin_once(node, timeout_sec=0.0)
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
