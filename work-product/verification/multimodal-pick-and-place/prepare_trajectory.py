#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from scene import CUBE_CENTERS, PANDA_HOME, PickPlaceScene, color_pixel_counts, matrix_to_numpy
from trajectory import solve_pose


TARGETS = [
    ("pregrasp", np.array([0.72, 0.36, 0.18], dtype=np.float64)),
    ("grasp", np.array([0.72, 0.19, 0.18], dtype=np.float64)),
    ("lift", np.array([0.72, 0.42, 0.18], dtype=np.float64)),
    ("transfer", np.array([0.72, 0.42, -0.18], dtype=np.float64)),
    ("place", np.array([0.72, 0.29, -0.18], dtype=np.float64)),
    ("retreat", np.array([0.72, 0.42, -0.18], dtype=np.float64)),
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("outputs"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    scene = PickPlaceScene.create(args.output)
    try:
        scene.set_joints(PANDA_HOME)
        _home_position, home_rotation = matrix_to_numpy(scene.hand_transform())

        before_overview = scene.render_overview()
        before_wrist = scene.render_wrist()
        counts = color_pixel_counts(before_wrist)
        cv2.imwrite(
            str(args.output / "before-overview.png"),
            cv2.cvtColor(before_overview, cv2.COLOR_RGB2BGR),
        )
        cv2.imwrite(
            str(args.output / "before-wrist.png"),
            cv2.cvtColor(before_wrist, cv2.COLOR_RGB2BGR),
        )
        if any(count < 300 for count in counts.values()):
            raise RuntimeError(f"home wrist view does not clearly show all colors: {counts}")

        solved = {"home": PANDA_HOME.copy()}
        seed = PANDA_HOME.copy()
        for name, position in TARGETS:
            seed = solve_pose(
                scene.sim,
                scene.arm,
                seed,
                position,
                home_rotation,
                scene.hand_link_id,
            )
            solved[name] = seed.copy()
            print(f"SOLVED {name} joints={seed.round(5).tolist()}", flush=True)

        solved["home_return"] = PANDA_HOME.copy()
        payload = {
            "cube_centers": {
                name: center.tolist() for name, center in CUBE_CENTERS.items()
            },
            "frames_per_segment": 24,
            "waypoints": [
                {"name": name, "joints": joints.tolist()}
                for name, joints in solved.items()
            ],
            "initial_wrist_color_pixels": counts,
        }
        (args.output / "trajectory.json").write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8"
        )
        print(f"TRAJECTORY written={args.output / 'trajectory.json'}", flush=True)
    finally:
        scene.close()


if __name__ == "__main__":
    main()
