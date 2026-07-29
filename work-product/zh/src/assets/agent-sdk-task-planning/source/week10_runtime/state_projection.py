from __future__ import annotations

from datetime import datetime

from robot_api.contracts import RobotState


_LOCATIONS = {"home", "indicator_station", "main_switch"}
_ARM_POSES = {"home", "ready", "press", "retract"}


def public_robot_state(
    payload: dict, *, captured_at: datetime
) -> RobotState:
    location = payload.get("location", "unknown")
    arm_pose = payload.get("arm_pose", "unknown")
    return RobotState(
        captured_at=captured_at,
        location=location if location in _LOCATIONS else "unknown",
        arm_pose=arm_pose if arm_pose in _ARM_POSES else "unknown",
        navigation_active=bool(payload.get("navigation_active", False)),
        arm_active=bool(payload.get("arm_active", False)),
        stopped=bool(payload.get("stopped", False)),
        pose=payload.get("pose"),
    )
