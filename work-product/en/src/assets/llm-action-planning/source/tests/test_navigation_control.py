import math
import sys
import unittest
from pathlib import Path


CONTROLLER_DIR = (
    Path(__file__).resolve().parents[1] / "controllers" / "action_controller"
)
sys.path.insert(0, str(CONTROLLER_DIR))

from navigation_control import (  # noqa: E402
    DriveCommand,
    compute_drive_command,
    limit_command,
    mecanum_wheel_speeds,
    pose_is_within_tolerance,
    ros_yaw_from_webots,
)


class NavigationControlTests(unittest.TestCase):
    def test_world_defines_mecanum_contact_properties(self):
        world_source = (
            CONTROLLER_DIR.parents[1] / "worlds" / "youbot_switch_office.wbt"
        ).read_text(encoding="utf-8")

        self.assertIn('material1 "InteriorWheelMat"', world_source)
        self.assertIn('material1 "ExteriorWheelMat"', world_source)
        self.assertIn("forceDependentSlip [", world_source)

    def test_webots_yaw_is_converted_to_ros_convention(self):
        self.assertAlmostEqual(ros_yaw_from_webots(0.4), -0.4)
        self.assertAlmostEqual(ros_yaw_from_webots(-0.4), 0.4)

    def test_controller_does_not_overwrite_dynamic_robot_pose(self):
        controller_source = (
            CONTROLLER_DIR / "action_controller.py"
        ).read_text(encoding="utf-8")

        self.assertNotIn("translation_field", controller_source)
        self.assertNotIn("rotation_field", controller_source)
        self.assertNotIn("self.self_node.resetPhysics()", controller_source)

    def test_skill_timeouts_cover_slow_rendered_simulation(self):
        runtime_source = (
            CONTROLLER_DIR.parents[1] / "action_planning" / "ros_skills.py"
        ).read_text(encoding="utf-8")

        self.assertIn(
            'ACTION_PLANNING_NAVIGATION_TIMEOUT_S", "180"',
            runtime_source,
        )
        self.assertIn(
            'ACTION_PLANNING_ARM_ACTION_TIMEOUT_S", "75"',
            runtime_source,
        )

    def test_goal_returns_zero_reached_command(self):
        command = compute_drive_command(
            current_x=1.0,
            current_y=2.0,
            current_yaw=0.1,
            target_x=1.03,
            target_y=2.02,
            target_yaw=0.1,
            position_tolerance=0.05,
        )

        self.assertTrue(command.reached)
        self.assertEqual(command, DriveCommand(0.0, 0.0, 0.0, True))

    def test_world_error_is_rotated_into_robot_frame(self):
        command = compute_drive_command(
            current_x=0.0,
            current_y=0.0,
            current_yaw=math.pi / 2.0,
            target_x=1.0,
            target_y=0.0,
            target_yaw=math.pi / 2.0,
            max_linear_speed=0.4,
            linear_gain=1.0,
        )

        self.assertAlmostEqual(command.vx, 0.0, places=7)
        self.assertAlmostEqual(command.vy, -0.4, places=7)
        self.assertAlmostEqual(command.omega, 0.0, places=7)
        self.assertFalse(command.reached)

    def test_command_change_is_acceleration_limited(self):
        limited = limit_command(
            DriveCommand(0.0, 0.0, 0.0),
            DriveCommand(0.4, -0.3, 1.0),
            linear_delta=0.05,
            angular_delta=0.1,
        )

        self.assertAlmostEqual(math.hypot(limited.vx, limited.vy), 0.05)
        self.assertAlmostEqual(limited.vx / limited.vy, -4.0 / 3.0)
        self.assertAlmostEqual(limited.omega, 0.1)

    def test_wheel_speeds_are_scaled_to_motor_limit(self):
        speeds = mecanum_wheel_speeds(
            DriveCommand(1.0, 0.5, 0.8),
            wheel_radius=0.05,
            geometry=0.386,
            max_wheel_speed=12.0,
        )

        self.assertEqual(len(speeds), 4)
        self.assertLessEqual(max(abs(speed) for speed in speeds), 12.0)
        self.assertAlmostEqual(max(abs(speed) for speed in speeds), 12.0)

    def test_positive_angular_velocity_turns_counterclockwise(self):
        speeds = mecanum_wheel_speeds(
            DriveCommand(0.0, 0.0, 0.5),
            wheel_radius=0.05,
            geometry=0.386,
            max_wheel_speed=12.0,
        )

        self.assertLess(speeds[0], 0.0)
        self.assertGreater(speeds[1], 0.0)
        self.assertLess(speeds[2], 0.0)
        self.assertGreater(speeds[3], 0.0)

    def test_positive_lateral_velocity_moves_left(self):
        speeds = mecanum_wheel_speeds(
            DriveCommand(0.0, 0.2, 0.0),
            wheel_radius=0.05,
            geometry=0.386,
            max_wheel_speed=12.0,
        )

        self.assertGreater(speeds[0], 0.0)
        self.assertLess(speeds[1], 0.0)
        self.assertLess(speeds[2], 0.0)
        self.assertGreater(speeds[3], 0.0)

    def test_pose_settling_requires_every_joint_to_reach_target(self):
        target = [0.0, 1.57, -2.635, 1.78, 0.0]

        self.assertTrue(
            pose_is_within_tolerance(
                [0.01, 1.56, -2.62, 1.79, -0.01],
                target,
                tolerance=0.02,
            )
        )
        self.assertFalse(
            pose_is_within_tolerance(
                [0.01, 1.56, -2.59, 1.79, -0.01],
                target,
                tolerance=0.02,
            )
        )


if __name__ == "__main__":
    unittest.main()
