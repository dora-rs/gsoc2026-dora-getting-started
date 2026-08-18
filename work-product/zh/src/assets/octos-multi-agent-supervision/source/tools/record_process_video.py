#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import signal
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String


SRC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SRC))

from process_runtime.control_cycles import (  # noqa: E402
    ControlEngagementTracker,
    StableCompletionGate,
    cap_engagement_counts,
)
from process_runtime.recording_layout import (  # noqa: E402
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    compose_recording_frame,
    recorder_should_stop,
)


def decode_image(message: Image) -> np.ndarray:
    channels = 4 if message.encoding in {"bgra8", "rgba8"} else 3
    frame = np.frombuffer(message.data, dtype=np.uint8).reshape(
        message.height,
        message.width,
        channels,
    )
    if message.encoding == "rgba8":
        return cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
    if message.encoding == "bgra8":
        return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
    if message.encoding == "rgb8":
        return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    return frame.copy()


class ProcessRecorder(Node):
    def __init__(
        self,
        output: Path,
        snapshots: Path,
        fps: float,
        target_engagements: int,
        stable_tail_seconds: float,
    ) -> None:
        super().__init__("process_mission_recorder")
        output.parent.mkdir(parents=True, exist_ok=True)
        snapshots.mkdir(parents=True, exist_ok=True)
        self.output = output
        self.snapshots = snapshots
        self.fps = fps
        self.target_engagements = target_engagements
        self.scene: np.ndarray | None = None
        self.observer: np.ndarray | None = None
        self.telemetry: dict = {}
        self.writer = cv2.VideoWriter(
            str(output),
            cv2.VideoWriter_fourcc(*"mp4v"),
            fps,
            (CANVAS_WIDTH, CANVAS_HEIGHT),
        )
        if not self.writer.isOpened():
            raise RuntimeError(f"could not open video writer for {output}")
        self.frame_count = 0
        self.saved: set[str] = set()
        self.last_frame: np.ndarray | None = None
        self.engagement_tracker = ControlEngagementTracker()
        self.completion_gate = StableCompletionGate(
            target_engagements=target_engagements,
            stable_seconds=stable_tail_seconds,
        )
        self.engagement_counts = {"cooling": 0, "relief": 0}
        self.previous_engagement_counts = dict(self.engagement_counts)
        self.recording_complete = False
        self.active_snapshots: set[tuple[str, int]] = set()
        self.create_subscription(
            Image,
            "/scene_camera/image_raw",
            self.on_scene,
            10,
        )
        self.create_subscription(
            Image,
            "/process/observer/camera/image_raw",
            self.on_observer,
            10,
        )
        self.create_subscription(
            String,
            "/process/plant/state",
            self.on_plant_state,
            10,
        )

    def on_scene(self, message: Image) -> None:
        self.scene = decode_image(message)

    def on_observer(self, message: Image) -> None:
        self.observer = decode_image(message)

    def on_plant_state(self, message: String) -> None:
        try:
            telemetry = json.loads(message.data)
        except json.JSONDecodeError:
            return
        self.previous_engagement_counts = dict(self.engagement_counts)
        raw_counts = self.engagement_tracker.update(telemetry)
        self.engagement_counts = cap_engagement_counts(
            raw_counts,
            target=self.target_engagements,
        )
        telemetry["cooling_engagement_count"] = self.engagement_counts[
            "cooling"
        ]
        telemetry["relief_engagement_count"] = self.engagement_counts[
            "relief"
        ]
        telemetry["engagement_target"] = self.target_engagements
        self.telemetry = telemetry

    def _save_once(self, name: str, frame: np.ndarray) -> None:
        if name in self.saved:
            return
        if not cv2.imwrite(str(self.snapshots / f"{name}.png"), frame):
            raise RuntimeError(f"failed to save snapshot {name}")
        self.saved.add(name)

    def _capture_milestones(
        self,
        frame: np.ndarray,
        *,
        now: float,
    ) -> None:
        self._save_once("01-scene-start", frame)
        if (
            self.telemetry.get("observer_docked")
            and self.telemetry.get("operator_at_control")
        ):
            self._save_once("02-both-robots-ready", frame)

        for control, field in (
            ("cooling", "cooling_on"),
            ("relief", "relief_open"),
        ):
            engagement_number = min(
                self.engagement_counts[control] + 1,
                self.target_engagements,
            )
            milestone = (control, engagement_number)
            if (
                self.telemetry.get(field)
                and milestone not in self.active_snapshots
            ):
                self._save_once(
                    f"{control}-{engagement_number}-active",
                    frame,
                )
                self.active_snapshots.add(milestone)
            if (
                self.engagement_counts[control]
                > self.previous_engagement_counts[control]
            ):
                self._save_once(
                    f"{control}-{self.engagement_counts[control]}-complete",
                    frame,
                )

        if recorder_should_stop(
            self.telemetry,
            self.engagement_counts,
            completion_gate=self.completion_gate,
            now=now,
        ):
            self._save_once("07-control-target-complete", frame)
            self.recording_complete = True

    def record_frame(self) -> bool:
        if self.scene is None or self.observer is None:
            return False
        frame = compose_recording_frame(
            self.scene,
            self.observer,
            self.telemetry,
        )
        self.writer.write(frame)
        self.frame_count += 1
        self.last_frame = frame
        self._capture_milestones(frame, now=time.monotonic())
        return True

    def close(self) -> None:
        if self.last_frame is not None and not self.recording_complete:
            self._save_once("99-recorder-end", self.last_frame)
        self.writer.release()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--snapshots", type=Path, required=True)
    parser.add_argument("--fps", type=float, default=10.0)
    parser.add_argument("--target-engagements", type=int, default=2)
    parser.add_argument("--stable-tail-seconds", type=float, default=4.0)
    parser.add_argument("--max-duration", type=float, default=600.0)
    args = parser.parse_args()

    rclpy.init()
    node = ProcessRecorder(
        args.output,
        args.snapshots,
        args.fps,
        args.target_engagements,
        args.stable_tail_seconds,
    )
    running = True

    def stop(*_args) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    started = time.monotonic()
    next_frame = started
    try:
        while running and time.monotonic() - started < args.max_duration:
            rclpy.spin_once(node, timeout_sec=0.02)
            now = time.monotonic()
            if now >= next_frame:
                node.record_frame()
                if node.recording_complete:
                    running = False
                next_frame += 1.0 / args.fps
                if next_frame < now - 1.0:
                    next_frame = now
    finally:
        node.close()
        node.destroy_node()
        rclpy.shutdown()
    print(
        json.dumps(
            {
                "output": str(args.output),
                "frames": node.frame_count,
                "fps": args.fps,
                "duration_seconds": round(
                    node.frame_count / args.fps,
                    2,
                ),
                "engagement_counts": node.engagement_counts,
                "engagement_target": args.target_engagements,
                "stable_tail_seconds": args.stable_tail_seconds,
                "snapshots": sorted(node.saved),
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
