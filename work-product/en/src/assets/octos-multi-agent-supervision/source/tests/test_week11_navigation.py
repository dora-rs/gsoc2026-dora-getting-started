import sys
from pathlib import Path


CONTROLLER_DIR = (
    Path(__file__).resolve().parents[1]
    / "controllers"
    / "week11_robot_controller"
)
sys.path.insert(0, str(CONTROLLER_DIR))

from navigation_control import compute_drive_command


def test_lateral_error_is_corrected_toward_the_route() -> None:
    above_route = compute_drive_command(
        current_x=0.0,
        current_y=1.5,
        current_yaw=0.0,
        target_x=2.0,
        target_y=1.35,
    )
    below_route = compute_drive_command(
        current_x=0.0,
        current_y=1.2,
        current_yaw=0.0,
        target_x=2.0,
        target_y=1.35,
    )

    assert above_route.vy < 0.0
    assert below_route.vy > 0.0
