import unittest

from test_plan_validator import canonical_plan
from week9_validation.mission import MissionMachine


def complete(machine, result):
    request = machine.next_request()
    if request is None:
        raise AssertionError("expected a skill request")
    machine.accept_result(request.step_id, result)
    return request


class MissionMachineTests(unittest.TestCase):
    def test_switch_on_executes_arm_and_second_observation(self):
        machine = MissionMachine(canonical_plan())
        self.assertEqual(complete(machine, {"status": "succeeded"}).skill, "navigate_to")
        self.assertEqual(
            complete(
                machine,
                {
                    "status": "succeeded",
                    "visible": True,
                    "state": "on",
                    "confidence": 0.99,
                },
            ).skill,
            "observe_switch",
        )
        self.assertEqual(
            complete(machine, {"status": "succeeded", "state": "off"}).skill,
            "set_switch_state",
        )
        self.assertEqual(
            complete(
                machine,
                {
                    "status": "succeeded",
                    "visible": True,
                    "state": "off",
                    "confidence": 0.99,
                },
            ).skill,
            "observe_switch",
        )
        self.assertEqual(complete(machine, {"status": "succeeded"}).skill, "navigate_to")
        self.assertIsNone(machine.next_request())
        self.assertEqual(machine.state, "SUCCEEDED")

    def test_switch_off_skips_arm_and_second_observation(self):
        machine = MissionMachine(canonical_plan())
        complete(machine, {"status": "succeeded"})
        complete(
            machine,
            {
                "status": "succeeded",
                "visible": True,
                "state": "off",
                "confidence": 0.99,
            },
        )
        request = machine.next_request()
        self.assertEqual(request.skill, "navigate_to")
        self.assertEqual(request.arguments, {"location": "home"})
        machine.accept_result(request.step_id, {"status": "succeeded"})
        self.assertIsNone(machine.next_request())
        self.assertEqual(machine.state, "SUCCEEDED")
        skipped = [
            event["step_id"]
            for event in machine.events
            if event["event"] == "STEP_SKIPPED"
        ]
        self.assertEqual(skipped, ["turn_off", "observe_after"])

    def test_failed_skill_fails_mission(self):
        machine = MissionMachine(canonical_plan())
        request = machine.next_request()
        machine.accept_result(
            request.step_id,
            {"status": "failed", "detail": "navigation rejected"},
        )
        self.assertEqual(machine.state, "FAILED")
        self.assertIsNone(machine.next_request())

    def test_post_action_observation_must_match_requested_state(self):
        machine = MissionMachine(canonical_plan())
        complete(machine, {"status": "succeeded"})
        complete(
            machine,
            {
                "status": "succeeded",
                "visible": True,
                "state": "on",
                "confidence": 0.95,
            },
        )
        complete(machine, {"status": "succeeded", "state": "off"})
        complete(
            machine,
            {
                "status": "succeeded",
                "visible": True,
                "state": "on",
                "confidence": 0.95,
            },
        )
        self.assertEqual(machine.state, "FAILED")
        self.assertEqual(
            machine.events[-1],
            {"event": "MISSION_FAILED", "failed_step": "observe_after"},
        )


if __name__ == "__main__":
    unittest.main()
