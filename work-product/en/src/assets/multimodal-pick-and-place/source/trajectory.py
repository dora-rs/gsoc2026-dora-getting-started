from __future__ import annotations

import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation


def carry_action_after_waypoint(name: str) -> str | None:
    if name == "grasp":
        return "attach"
    if name == "place":
        return "release"
    return None


def interpolate_segment(
    start: np.ndarray, end: np.ndarray, frames: int
) -> np.ndarray:
    if frames < 2:
        raise ValueError("frames must be at least 2")
    start = np.asarray(start, dtype=np.float64)
    end = np.asarray(end, dtype=np.float64)
    if start.shape != end.shape:
        raise ValueError("start and end must have the same shape")

    t = np.linspace(0.0, 1.0, frames, dtype=np.float64)
    blend = 6.0 * t**5 - 15.0 * t**4 + 10.0 * t**3
    return start[None, :] + blend[:, None] * (end - start)[None, :]


def validate_joint_path(
    path: np.ndarray, lower: np.ndarray, upper: np.ndarray
) -> None:
    path = np.asarray(path, dtype=np.float64)
    lower = np.asarray(lower, dtype=np.float64)
    upper = np.asarray(upper, dtype=np.float64)
    if path.ndim != 2 or path.shape[1:] != lower.shape or lower.shape != upper.shape:
        raise ValueError("joint path and limits have incompatible shapes")
    if not np.all(np.isfinite(path)):
        raise ValueError("joint path contains non-finite values")
    if np.any(path < lower[None, :] - 1e-8) or np.any(path > upper[None, :] + 1e-8):
        raise ValueError("joint path exceeds joint limits")


def solve_pose(
    sim,
    arm,
    seed: np.ndarray,
    target_position: np.ndarray,
    target_rotation: np.ndarray,
    hand_link_id: int,
) -> np.ndarray:
    lower, upper = arm.joint_position_limits
    lower = np.asarray(lower[:7], dtype=np.float64)
    upper = np.asarray(upper[:7], dtype=np.float64)
    seed = np.clip(np.asarray(seed, dtype=np.float64), lower, upper)
    target_position = np.asarray(target_position, dtype=np.float64)
    target_rotation = np.asarray(target_rotation, dtype=np.float64)

    def residual(joints: np.ndarray) -> np.ndarray:
        arm.joint_positions = joints.tolist()
        sim.step_physics(1.0 / 240.0)
        transform = arm.get_link_scene_node(hand_link_id).absolute_transformation()
        position = np.array(
            [float(transform.translation[i]) for i in range(3)], dtype=np.float64
        )
        rotation = np.array(
            [
                [float(transform.rotation()[col][row]) for col in range(3)]
                for row in range(3)
            ],
            dtype=np.float64,
        )
        rotation_error = Rotation.from_matrix(target_rotation.T @ rotation).as_rotvec()
        return np.concatenate(
            [
                8.0 * (position - target_position),
                0.8 * rotation_error,
                0.015 * (joints - seed),
            ]
        )

    solved = least_squares(
        residual,
        seed,
        bounds=(lower, upper),
        xtol=1e-10,
        ftol=1e-10,
        gtol=1e-10,
        diff_step=1e-4,
        max_nfev=600,
    )
    joints = solved.x.astype(np.float64)
    final = residual(joints)
    position_error = np.linalg.norm(final[:3]) / 8.0
    orientation_error = np.linalg.norm(final[3:6]) / 0.8
    if not solved.success or position_error > 0.012 or orientation_error > 0.10:
        raise RuntimeError(
            "IK failed: "
            f"success={solved.success} position_error={position_error:.4f} "
            f"orientation_error={orientation_error:.4f}"
        )
    return joints


def concatenate_segments(waypoints: list[np.ndarray], frames: int) -> np.ndarray:
    if len(waypoints) < 2:
        raise ValueError("at least two waypoints are required")
    segments = [
        interpolate_segment(start, end, frames)
        for start, end in zip(waypoints, waypoints[1:])
    ]
    return np.vstack([segments[0], *[segment[1:] for segment in segments[1:]]])
