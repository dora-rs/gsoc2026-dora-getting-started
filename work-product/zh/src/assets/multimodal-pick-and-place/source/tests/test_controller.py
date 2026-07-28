import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from contracts import ObservationResult  # noqa: E402
from controller import Command, State, TaskController  # noqa: E402


VISIBLE_SEPARATE = ObservationResult(True, True, False, 0.98)
VISIBLE_STACKED = ObservationResult(True, True, True, 0.97)


class TaskControllerTests(unittest.TestCase):
    def test_successful_flow_requires_before_motion_and_after_analysis(self):
        controller = TaskController(min_confidence=0.8)

        self.assertEqual(controller.start(), [Command("capture", "before")])
        self.assertEqual(controller.state, State.INSPECTING_BEFORE)

        self.assertEqual(
            controller.on_analysis("before", VISIBLE_SEPARATE),
            [Command("run_pick_place")],
        )
        self.assertEqual(controller.state, State.MOVING)

        self.assertEqual(
            controller.on_motion_complete(success=True),
            [Command("capture", "after")],
        )
        self.assertEqual(controller.state, State.INSPECTING_AFTER)

        self.assertEqual(
            controller.on_analysis("after", VISIBLE_STACKED),
            [Command("task_success")],
        )
        self.assertEqual(controller.state, State.SUCCEEDED)

    def test_does_not_move_when_initial_condition_fails(self):
        controller = TaskController()
        controller.start()

        commands = controller.on_analysis(
            "before", ObservationResult(True, False, False, 0.99)
        )

        self.assertEqual(commands, [Command("task_failed", "precondition")])
        self.assertEqual(controller.state, State.FAILED)

    def test_does_not_move_on_low_confidence(self):
        controller = TaskController(min_confidence=0.8)
        controller.start()

        commands = controller.on_analysis(
            "before", ObservationResult(True, True, False, 0.79)
        )

        self.assertEqual(commands, [Command("task_failed", "precondition")])
        self.assertEqual(controller.state, State.FAILED)

    def test_final_visual_failure_marks_task_failed(self):
        controller = TaskController()
        controller.start()
        controller.on_analysis("before", VISIBLE_SEPARATE)
        controller.on_motion_complete(success=True)

        commands = controller.on_analysis("after", VISIBLE_SEPARATE)

        self.assertEqual(commands, [Command("task_failed", "postcondition")])
        self.assertEqual(controller.state, State.FAILED)

    def test_rejects_stale_phase(self):
        controller = TaskController()
        controller.start()

        with self.assertRaisesRegex(RuntimeError, "phase"):
            controller.on_analysis("after", VISIBLE_STACKED)

    def test_motion_failure_stops_the_task(self):
        controller = TaskController()
        controller.start()
        controller.on_analysis("before", VISIBLE_SEPARATE)

        commands = controller.on_motion_complete(success=False)

        self.assertEqual(commands, [Command("task_failed", "motion")])
        self.assertEqual(controller.state, State.FAILED)


if __name__ == "__main__":
    unittest.main()
