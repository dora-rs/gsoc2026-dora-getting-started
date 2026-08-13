#!/usr/bin/env python3
import argparse
from pathlib import Path

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image


class ImageCapture(Node):
    def __init__(self, topic: str, output: Path) -> None:
        super().__init__("process_image_capture")
        self.output = output
        self.saved = False
        self.create_subscription(Image, topic, self.on_image, 10)

    def on_image(self, message: Image) -> None:
        if self.saved:
            return
        channels = 4 if message.encoding in {"bgra8", "rgba8"} else 3
        frame = np.frombuffer(message.data, dtype=np.uint8).reshape(
            message.height, message.width, channels
        )
        if message.encoding == "rgba8":
            frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGRA)
        elif message.encoding == "rgb8":
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        self.output.parent.mkdir(parents=True, exist_ok=True)
        if not cv2.imwrite(str(self.output), frame):
            raise RuntimeError(f"failed to write {self.output}")
        self.saved = True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()

    rclpy.init()
    node = ImageCapture(args.topic, args.output)
    started = node.get_clock().now()
    try:
        while not node.saved:
            rclpy.spin_once(node, timeout_sec=0.2)
            elapsed = (node.get_clock().now() - started).nanoseconds / 1e9
            if elapsed > args.timeout:
                raise TimeoutError(f"no image received from {args.topic}")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
