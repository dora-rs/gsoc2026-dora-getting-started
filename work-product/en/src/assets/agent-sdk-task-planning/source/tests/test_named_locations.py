import json
import math
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def test_three_named_locations_are_evenly_spaced():
    locations = json.loads(
        (ROOT / "config" / "locations.json").read_text(encoding="utf-8")
    )
    assert set(locations) == {"home", "indicator_station", "main_switch"}

    def distance(left, right):
        return math.hypot(
            locations[right]["x"] - locations[left]["x"],
            locations[right]["y"] - locations[left]["y"],
        )

    first = distance("home", "indicator_station")
    second = distance("indicator_station", "main_switch")
    assert first == pytest.approx(second, abs=0.01)


def test_location_config_contains_bounded_pose_not_motion_commands():
    text = (ROOT / "config" / "locations.json").read_text(encoding="utf-8")
    assert "linear_velocity" not in text
    assert "wheel_speed" not in text
    assert "joint" not in text


def test_named_locations_share_the_validated_corridor_heading():
    locations = json.loads(
        (ROOT / "config" / "locations.json").read_text(encoding="utf-8")
    )

    assert {pose["y"] for pose in locations.values()} == {-1.8}
    assert {pose["yaw"] for pose in locations.values()} == {0.0}
