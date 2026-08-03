from datetime import datetime, timezone

from week10_runtime.state_projection import public_robot_state


def test_public_state_keeps_motion_truth_but_hides_switch_ground_truth():
    now = datetime.now(timezone.utc)
    state = public_robot_state(
        {
            "location": "indicator_station",
            "arm_pose": "home",
            "switch_state": "on",
            "navigation_active": False,
            "arm_active": False,
            "stopped": False,
            "pose": {"x": 0.175, "y": -1.8, "yaw": -1.5708},
        },
        captured_at=now,
    )

    assert state.location == "indicator_station"
    assert state.captured_at == now
    assert "switch_state" not in state.model_dump()


def test_unknown_location_is_preserved_as_unknown():
    state = public_robot_state(
        {
            "location": "not-at-a-named-pose",
            "arm_pose": "home",
            "navigation_active": True,
            "arm_active": False,
            "stopped": False,
            "pose": None,
        },
        captured_at=datetime.now(timezone.utc),
    )
    assert state.location == "unknown"
