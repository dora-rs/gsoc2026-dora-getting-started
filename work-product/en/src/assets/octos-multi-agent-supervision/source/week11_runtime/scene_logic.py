from dataclasses import dataclass, replace
from math import hypot


@dataclass(frozen=True)
class Pose2D:
    x: float
    y: float
    heading_deg: float


def _heading_error_deg(actual: float, expected: float) -> float:
    return abs((actual - expected + 180.0) % 360.0 - 180.0)


def is_pose_reached(
    robot_pose: Pose2D,
    target_pose: Pose2D,
    *,
    position_tolerance_m: float = 0.16,
    heading_tolerance_deg: float = 12.0,
) -> bool:
    return (
        hypot(robot_pose.x - target_pose.x, robot_pose.y - target_pose.y)
        <= position_tolerance_m
        and _heading_error_deg(robot_pose.heading_deg, target_pose.heading_deg)
        <= heading_tolerance_deg
    )


def is_observer_docked(robot_pose: Pose2D, station_pose: Pose2D) -> bool:
    return is_pose_reached(
        robot_pose,
        station_pose,
        position_tolerance_m=0.14,
        heading_tolerance_deg=10.0,
    )


def should_start_process(
    *,
    phase: str,
    observer_docked: bool,
    operator_at_control: bool,
) -> bool:
    del observer_docked, operator_at_control
    return phase == "idle"


@dataclass(frozen=True)
class ControlStation:
    pose: Pose2D

    def contains(self, robot_pose: Pose2D) -> bool:
        return is_pose_reached(
            robot_pose,
            self.pose,
            position_tolerance_m=0.18,
            heading_tolerance_deg=12.0,
        )


@dataclass(frozen=True)
class SwitchState:
    cooling_on: bool = False
    relief_open: bool = False


class SwitchPanel:
    _ARM_POSES = {
        "cooling": "press_cooling",
        "relief": "press_relief",
    }

    def __init__(self) -> None:
        self._state = SwitchState()

    @property
    def state(self) -> SwitchState:
        return self._state

    def apply(
        self,
        *,
        switch_name: str,
        enabled: bool,
        robot_pose: Pose2D,
        arm_pose_name: str,
        station: ControlStation,
    ) -> SwitchState:
        if switch_name not in self._ARM_POSES:
            raise ValueError(f"unknown switch: {switch_name}")
        if not station.contains(robot_pose):
            raise PermissionError("operator is not at the control station")
        if arm_pose_name != self._ARM_POSES[switch_name]:
            raise ValueError(
                f"{switch_name} requires verified arm pose "
                f"{self._ARM_POSES[switch_name]}"
            )

        if switch_name == "cooling":
            self._state = replace(self._state, cooling_on=enabled)
        else:
            self._state = replace(self._state, relief_open=enabled)
        return self._state
