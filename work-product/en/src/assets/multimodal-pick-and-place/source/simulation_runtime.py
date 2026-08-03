from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

from scene import FPS, HEIGHT, PANDA_HOME, WIDTH, PickPlaceScene, color_pixel_counts
from trajectory import carry_action_after_waypoint, interpolate_segment


class SimulationSession:
    def __init__(self, output_dir: Path, trajectory_path: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        payload = json.loads(trajectory_path.read_text(encoding="utf-8"))
        self.frames_per_segment = int(payload["frames_per_segment"])
        self.waypoints = [
            (entry["name"], np.asarray(entry["joints"], dtype=np.float64))
            for entry in payload["waypoints"]
        ]
        self.scene = PickPlaceScene.create(output_dir)
        self.scene.set_joints(PANDA_HOME)

    def close(self) -> None:
        self.scene.close()

    def capture(self, phase: str) -> dict[str, object]:
        overview = self.scene.render_overview()
        wrist = self.scene.render_wrist()
        overview_path = self.output_dir / f"{phase}-overview.png"
        wrist_path = self.output_dir / f"{phase}-wrist.png"
        self._write_image(overview_path, overview)
        self._write_image(wrist_path, wrist)
        return {
            "phase": phase,
            "overview_path": str(overview_path.resolve()),
            "wrist_path": str(wrist_path.resolve()),
            "wrist_color_pixels": color_pixel_counts(wrist),
        }

    def run_pick_place(self) -> dict[str, object]:
        overview_writer = self._writer(
            self.output_dir / "pick-place-overview.mp4", WIDTH, HEIGHT
        )
        wrist_writer = self._writer(
            self.output_dir / "pick-place-wrist.mp4", WIDTH, HEIGHT
        )
        combined_width, combined_height = 1280, 360
        combined_writer = self._writer(
            self.output_dir / "pick-place-side-by-side.mp4",
            combined_width,
            combined_height,
        )

        attached_transform = None
        frame_count = 0

        def record_frame() -> None:
            nonlocal frame_count
            overview = self.scene.render_overview()
            wrist = self.scene.render_wrist()
            overview_writer.write(cv2.cvtColor(overview, cv2.COLOR_RGB2BGR))
            wrist_writer.write(cv2.cvtColor(wrist, cv2.COLOR_RGB2BGR))
            left = cv2.resize(overview, (640, 360), interpolation=cv2.INTER_AREA)
            right = cv2.resize(wrist, (640, 360), interpolation=cv2.INTER_AREA)
            combined = np.hstack([left, right])
            combined_writer.write(cv2.cvtColor(combined, cv2.COLOR_RGB2BGR))
            frame_count += 1

        try:
            for _ in range(FPS):
                record_frame()

            for (source_name, source), (destination_name, destination) in zip(
                self.waypoints, self.waypoints[1:]
            ):
                path = interpolate_segment(
                    source, destination, self.frames_per_segment
                )
                for joints in path[1:]:
                    self.scene.set_joints(joints)
                    if attached_transform is not None:
                        self.scene.update_attached_red(attached_transform)
                    record_frame()

                action = carry_action_after_waypoint(destination_name)
                if action == "attach":
                    attached_transform = self.scene.attach_red_to_hand()
                elif action == "release":
                    self.scene.place_red_on_blue()
                    attached_transform = None

            for _ in range(FPS):
                record_frame()
        finally:
            overview_writer.release()
            wrist_writer.release()
            combined_writer.release()

        home_error = float(
            np.max(np.abs(np.asarray(self.scene.arm.joint_positions[:7]) - PANDA_HOME))
        )
        red = self.scene.cube_center("red")
        blue = self.scene.cube_center("blue")
        stack_error = float(
            np.linalg.norm(red - (blue + np.array([0.0, 0.10, 0.0])))
        )
        return {
            "success": home_error < 1e-5 and stack_error < 1e-5,
            "frames": frame_count,
            "duration_seconds": frame_count / FPS,
            "home_error": home_error,
            "stack_error": stack_error,
            "overview_video": str(
                (self.output_dir / "pick-place-overview.mp4").resolve()
            ),
            "wrist_video": str(
                (self.output_dir / "pick-place-wrist.mp4").resolve()
            ),
            "side_by_side_video": str(
                (self.output_dir / "pick-place-side-by-side.mp4").resolve()
            ),
        }

    @staticmethod
    def _writer(path: Path, width: int, height: int) -> cv2.VideoWriter:
        writer = cv2.VideoWriter(
            str(path), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (width, height)
        )
        if not writer.isOpened():
            raise RuntimeError(f"could not open video writer: {path}")
        return writer

    @staticmethod
    def _write_image(path: Path, rgb: np.ndarray) -> None:
        if not cv2.imwrite(str(path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)):
            raise RuntimeError(f"could not write image: {path}")
