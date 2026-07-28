from mission_state import MissionGate


def complete_sensor_payload():
    return {
        "scan_samples": 4,
        "odom_samples": 4,
        "map": {"width": 219, "height": 220, "known_cells": 9200},
        "map_pose": {"x": -2.8, "y": 2.4, "yaw": 2.5},
    }


def test_gate_waits_for_all_required_inputs():
    gate = MissionGate()
    gate.update_sensors({"scan_samples": 1, "odom_samples": 1})
    assert not gate.ready
    assert gate.state == "WAITING_FOR_SENSORS"


def test_gate_becomes_ready_for_navigation():
    gate = MissionGate()
    gate.update_sensors(complete_sensor_payload())
    assert gate.ready
    assert gate.state == "READY"


def test_gate_tracks_navigation_success():
    gate = MissionGate()
    gate.update_sensors(complete_sensor_payload())
    gate.mark_goal_sent()
    gate.mark_goal_accepted()
    gate.update_feedback(1.25)
    gate.complete(True, "Target reached")
    result = gate.as_dict()
    assert result["state"] == "SUCCEEDED"
    assert result["distance_remaining"] == 1.25
    assert result["sensors"]["pose_available"]


def test_gate_tracks_navigation_failure():
    gate = MissionGate()
    gate.update_sensors(complete_sensor_payload())
    gate.mark_goal_sent()
    gate.complete(False, "Goal rejected")
    assert gate.state == "FAILED"
    assert gate.detail == "Goal rejected"
