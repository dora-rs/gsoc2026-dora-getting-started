import unittest

from week9_validation.plan_validator import validate_plan


def canonical_plan():
    return {
        "schema": "week9.action-plan.v1",
        "goal": "ensure main_switch is off and return home",
        "steps": [
            {
                "id": "go_to_switch",
                "skill": "navigate_to",
                "arguments": {"location": "main_switch"},
            },
            {
                "id": "observe_before",
                "skill": "observe_switch",
                "arguments": {"switch_id": "main_switch"},
                "save_as": "before",
            },
            {
                "id": "turn_off",
                "skill": "set_switch_state",
                "arguments": {"switch_id": "main_switch", "state": "off"},
                "when": {
                    "all": [
                        {"ref": "before.visible", "op": "eq", "value": True},
                        {"ref": "before.state", "op": "eq", "value": "on"},
                    ]
                },
            },
            {
                "id": "observe_after",
                "skill": "observe_switch",
                "arguments": {"switch_id": "main_switch"},
                "save_as": "after",
                "when": {
                    "ref": "turn_off.status",
                    "op": "eq",
                    "value": "succeeded",
                },
            },
            {
                "id": "return_home",
                "skill": "navigate_to",
                "arguments": {"location": "home"},
            },
        ],
    }


class PlanValidatorTests(unittest.TestCase):
    def test_accepts_canonical_plan(self):
        self.assertTrue(validate_plan(canonical_plan()).valid)

    def test_rejects_raw_coordinates(self):
        plan = canonical_plan()
        plan["steps"][0]["arguments"] = {"x": 1.0, "y": 2.0}
        result = validate_plan(plan)
        self.assertFalse(result.valid)
        self.assertTrue(any("forbidden" in error for error in result.errors))

    def test_rejects_raw_joint_command(self):
        plan = canonical_plan()
        plan["steps"].insert(
            -1,
            {
                "id": "raw_arm",
                "skill": "set_switch_state",
                "arguments": {
                    "switch_id": "main_switch",
                    "state": "off",
                    "joint_angles": [0, 1, 2, 3, 4],
                },
                "when": {"ref": "before.state", "op": "eq", "value": "on"},
            },
        )
        result = validate_plan(plan)
        self.assertFalse(result.valid)
        self.assertTrue(any("joint_angles" in error for error in result.errors))

    def test_rejects_unknown_skill(self):
        plan = canonical_plan()
        plan["steps"][2]["skill"] = "run_shell"
        self.assertFalse(validate_plan(plan).valid)

    def test_rejects_forward_reference(self):
        plan = canonical_plan()
        plan["steps"][0]["when"] = {
            "ref": "before.state",
            "op": "eq",
            "value": "on",
        }
        self.assertFalse(validate_plan(plan).valid)

    def test_rejects_duplicate_step_id(self):
        plan = canonical_plan()
        plan["steps"][1]["id"] = "go_to_switch"
        self.assertFalse(validate_plan(plan).valid)

    def test_rejects_unconditional_switch_action(self):
        plan = canonical_plan()
        del plan["steps"][2]["when"]
        self.assertFalse(validate_plan(plan).valid)

    def test_rejects_missing_return_home(self):
        plan = canonical_plan()
        plan["steps"] = plan["steps"][:-1]
        self.assertFalse(validate_plan(plan).valid)


if __name__ == "__main__":
    unittest.main()
