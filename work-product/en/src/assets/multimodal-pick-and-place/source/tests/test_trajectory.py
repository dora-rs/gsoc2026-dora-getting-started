import sys
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from trajectory import (  # noqa: E402
    carry_action_after_waypoint,
    interpolate_segment,
    validate_joint_path,
)


class TrajectoryTests(unittest.TestCase):
    def test_interpolation_preserves_endpoints(self):
        start = np.array([0.0, -0.5, 0.2], dtype=np.float64)
        end = np.array([0.8, 0.1, -0.3], dtype=np.float64)

        path = interpolate_segment(start, end, frames=21)

        np.testing.assert_allclose(path[0], start)
        np.testing.assert_allclose(path[-1], end)
        self.assertEqual(path.shape, (21, 3))

    def test_interpolation_starts_and_ends_smoothly(self):
        path = interpolate_segment(
            np.zeros(2, dtype=np.float64),
            np.ones(2, dtype=np.float64),
            frames=101,
        )

        start_step = np.linalg.norm(path[1] - path[0])
        middle_step = np.linalg.norm(path[51] - path[50])
        end_step = np.linalg.norm(path[-1] - path[-2])
        self.assertLess(start_step, middle_step * 0.02)
        self.assertLess(end_step, middle_step * 0.02)

    def test_rejects_path_outside_joint_limits(self):
        path = np.array([[0.0, 0.0], [0.2, 1.1]], dtype=np.float64)
        lower = np.array([-1.0, -1.0], dtype=np.float64)
        upper = np.array([1.0, 1.0], dtype=np.float64)

        with self.assertRaisesRegex(ValueError, "joint limits"):
            validate_joint_path(path, lower, upper)

    def test_accepts_path_inside_joint_limits(self):
        path = np.array([[0.0, 0.0], [0.2, 0.9]], dtype=np.float64)
        lower = np.array([-1.0, -1.0], dtype=np.float64)
        upper = np.array([1.0, 1.0], dtype=np.float64)

        validate_joint_path(path, lower, upper)

    def test_cube_is_attached_after_grasp_and_released_after_place(self):
        self.assertEqual(carry_action_after_waypoint("grasp"), "attach")
        self.assertEqual(carry_action_after_waypoint("place"), "release")
        self.assertIsNone(carry_action_after_waypoint("transfer"))


if __name__ == "__main__":
    unittest.main()
