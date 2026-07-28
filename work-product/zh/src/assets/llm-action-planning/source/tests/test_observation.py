import unittest

from week9_validation.contracts import parse_switch_observation


class ObservationTests(unittest.TestCase):
    def test_accepts_valid_observation(self):
        value = parse_switch_observation(
            {
                "switch_id": "main_switch",
                "visible": True,
                "state": "on",
                "confidence": 0.98,
            }
        )
        self.assertEqual(value.state, "on")

    def test_rejects_bad_confidence(self):
        with self.assertRaises(ValueError):
            parse_switch_observation(
                {
                    "switch_id": "main_switch",
                    "visible": True,
                    "state": "off",
                    "confidence": 1.2,
                }
            )

    def test_rejects_unexpected_fields(self):
        with self.assertRaises(ValueError):
            parse_switch_observation(
                {
                    "switch_id": "main_switch",
                    "visible": True,
                    "state": "on",
                    "confidence": 0.9,
                    "joint_angles": [1, 2, 3],
                }
            )


if __name__ == "__main__":
    unittest.main()
