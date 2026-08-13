from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class DriveCommand:
    vx: float
    vy: float
    omega: float
    reached: bool = False


def _clamp(value: float, limit: float) -> float:
    return max(-limit, min(limit, value))


def _angle_error(target: float, current: float) -> float:
    return math.atan2(math.sin(target - current), math.cos(target - current))


def ros_yaw_from_webots(webots_yaw: float) -> float:
    return math.atan2(math.sin(-webots_yaw), math.cos(-webots_yaw))


def pose_is_within_tolerance(
    current: list[float],
    target: list[float],
    *,
    tolerance: float,
) -> bool:
    return len(current) == len(target) and all(
        abs(value - expected) <= tolerance
        for value, expected in zip(current, target)
    )


def compute_drive_command(
    *,
    current_x: float,
    current_y: float,
    current_yaw: float,
    target_x: float,
    target_y: float,
    target_yaw: float = 0.0,
    position_tolerance: float = 0.07,
    yaw_tolerance: float = 0.08,
    linear_gain: float = 1.2,
    angular_gain: float = 2.0,
    max_linear_speed: float = 0.42,
    max_angular_speed: float = 0.7,
) -> DriveCommand:
    dx = target_x - current_x
    dy = target_y - current_y
    distance = math.hypot(dx, dy)
    yaw_error = _angle_error(target_yaw, current_yaw)
    if distance <= position_tolerance and abs(yaw_error) <= yaw_tolerance:
        return DriveCommand(0.0, 0.0, 0.0, True)

    world_speed = min(max_linear_speed, linear_gain * distance)
    if distance > 0.0:
        world_vx = world_speed * dx / distance
        world_vy = world_speed * dy / distance
    else:
        world_vx = world_vy = 0.0
    body_vx = math.cos(current_yaw) * world_vx + math.sin(current_yaw) * world_vy
    body_vy = -math.sin(current_yaw) * world_vx + math.cos(current_yaw) * world_vy
    omega = _clamp(angular_gain * yaw_error, max_angular_speed)
    return DriveCommand(body_vx, body_vy, omega)


def limit_command(
    previous: DriveCommand,
    target: DriveCommand,
    *,
    linear_delta: float,
    angular_delta: float,
) -> DriveCommand:
    if target.reached:
        return target
    delta_vx = target.vx - previous.vx
    delta_vy = target.vy - previous.vy
    delta_length = math.hypot(delta_vx, delta_vy)
    if delta_length > linear_delta:
        scale = linear_delta / delta_length
        delta_vx *= scale
        delta_vy *= scale
    omega = previous.omega + _clamp(
        target.omega - previous.omega,
        angular_delta,
    )
    return DriveCommand(
        previous.vx + delta_vx,
        previous.vy + delta_vy,
        omega,
    )


def mecanum_wheel_speeds(
    command: DriveCommand,
    *,
    wheel_radius: float,
    geometry: float,
    max_wheel_speed: float,
) -> list[float]:
    speeds = [
        (command.vx + command.vy - geometry * command.omega) / wheel_radius,
        (command.vx - command.vy + geometry * command.omega) / wheel_radius,
        (command.vx - command.vy - geometry * command.omega) / wheel_radius,
        (command.vx + command.vy + geometry * command.omega) / wheel_radius,
    ]
    largest = max(abs(speed) for speed in speeds)
    if largest > max_wheel_speed:
        scale = max_wheel_speed / largest
        speeds = [speed * scale for speed in speeds]
    return speeds
