import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from contracts import ObservationResult, parse_observation  # noqa: E402


class ObservationContractTests(unittest.TestCase):
    def test_parses_valid_closed_result(self):
        result = parse_observation(
            json.dumps(
                {
                    "red_visible": True,
                    "blue_visible": True,
                    "red_on_blue": False,
                    "confidence": 0.96,
                }
            )
        )
        self.assertEqual(
            result,
            ObservationResult(
                red_visible=True,
                blue_visible=True,
                red_on_blue=False,
                confidence=0.96,
            ),
        )

    def test_rejects_extra_fields(self):
        with self.assertRaisesRegex(ValueError, "fields"):
            parse_observation(
                json.dumps(
                    {
                        "red_visible": True,
                        "blue_visible": True,
                        "red_on_blue": False,
                        "confidence": 0.96,
                        "action": "move",
                    }
                )
            )

    def test_rejects_non_boolean_flags(self):
        with self.assertRaisesRegex(TypeError, "red_visible"):
            parse_observation(
                json.dumps(
                    {
                        "red_visible": "yes",
                        "blue_visible": True,
                        "red_on_blue": False,
                        "confidence": 0.96,
                    }
                )
            )

    def test_rejects_confidence_outside_unit_interval(self):
        with self.assertRaisesRegex(ValueError, "confidence"):
            parse_observation(
                json.dumps(
                    {
                        "red_visible": True,
                        "blue_visible": True,
                        "red_on_blue": False,
                        "confidence": 1.1,
                    }
                )
            )


if __name__ == "__main__":
    unittest.main()
