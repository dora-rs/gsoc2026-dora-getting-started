import math
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
CONTROLLER = ROOT / "controllers" / "week10_controller"
sys.path.insert(0, str(CONTROLLER))

from navigation_control import compute_drive_command


def test_navigation_reverses_without_turning_on_the_validated_corridor():
    command = compute_drive_command(
        current_x=0.0,
        current_y=0.0,
        current_yaw=0.0,
        target_x=-2.0,
        target_y=0.0,
        target_yaw=0.0,
    )

    assert command.vx < 0.0
    assert command.vy == pytest.approx(0.0)
    assert command.omega == pytest.approx(0.0)


def test_navigation_drives_forward_on_the_validated_corridor():
    command = compute_drive_command(
        current_x=0.0,
        current_y=0.0,
        current_yaw=0.0,
        target_x=2.0,
        target_y=0.0,
        target_yaw=0.0,
    )

    assert command.vx > 0.0
    assert command.vy == pytest.approx(0.0)
    assert command.omega == pytest.approx(0.0)


def test_navigation_aligns_to_corridor_before_reversing():
    command = compute_drive_command(
        current_x=2.0,
        current_y=0.0,
        current_yaw=math.pi / 2,
        target_x=0.0,
        target_y=0.0,
        target_yaw=math.pi / 2,
    )

    assert command.vx == pytest.approx(0.0)
    assert command.vy == pytest.approx(0.0)
    assert command.omega < 0.0


def test_navigation_defers_final_station_yaw_until_position_is_reached():
    command = compute_drive_command(
        current_x=2.0,
        current_y=0.0,
        current_yaw=0.0,
        target_x=0.0,
        target_y=0.0,
        target_yaw=math.pi / 2,
    )

    assert command.vx < 0.0
    assert command.vy == pytest.approx(0.0)
    assert command.omega == pytest.approx(0.0)


def test_navigation_corrects_orientation_after_reaching_position():
    command = compute_drive_command(
        current_x=1.98,
        current_y=0.0,
        current_yaw=0.5,
        target_x=2.0,
        target_y=0.0,
        target_yaw=0.0,
    )

    assert command.vx == pytest.approx(0.0)
    assert command.vy == pytest.approx(0.0)
    assert command.omega < 0.0
    assert not command.reached
