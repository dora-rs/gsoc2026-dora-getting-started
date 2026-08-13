import numpy as np

from process_runtime.control_cycles import StableCompletionGate
from process_runtime.recording_layout import (
    compose_recording_frame,
    engagement_progress_labels,
    recorder_should_stop,
    robot_status_label,
    valve_indicator_color,
)


def test_recording_frame_has_two_equal_views_and_fixed_canvas() -> None:
    scene = np.full((540, 960, 3), (10, 20, 30), dtype=np.uint8)
    observer = np.full((360, 640, 3), (40, 50, 60), dtype=np.uint8)

    result = compose_recording_frame(
        scene,
        observer,
        {
            "temperature_c": 58.5,
            "pressure_kpa": 198.0,
            "temperature_safe_min_c": 30.0,
            "temperature_safe_max_c": 60.0,
            "pressure_safe_min_kpa": 160.0,
            "pressure_safe_max_kpa": 200.0,
            "temperature_rate_c_per_s": 0.22,
            "pressure_rate_kpa_per_s": 0.65,
            "cooling_on": False,
            "relief_open": False,
            "observer_docked": True,
            "operator_at_control": True,
            "agent_action": "Supervisor: checking both observations",
            "cooling_engagement_count": 1,
            "relief_engagement_count": 2,
            "engagement_target": 2,
        },
    )

    assert result.shape == (720, 1920, 3)
    assert result[200, 200].tolist() == [10, 20, 30]
    assert result[200, 1200].tolist() == [40, 50, 60]
    assert result[550, 960].tolist() != [225, 232, 235]


def test_recording_status_distinguishes_home_from_moving() -> None:
    assert robot_status_label("home", False, "DOCKED") == "HOME"
    assert robot_status_label("station", True, "DOCKED") == "DOCKED"
    assert robot_status_label("route", False, "DOCKED") == "MOVING"


def test_recorder_stops_only_after_both_engagement_targets_are_stable() -> None:
    telemetry = {
        "temperature_c": 50.0,
        "pressure_kpa": 180.0,
        "temperature_safe_min_c": 30.0,
        "temperature_safe_max_c": 60.0,
        "pressure_safe_min_kpa": 160.0,
        "pressure_safe_max_kpa": 200.0,
        "cooling_on": False,
        "relief_open": False,
    }
    gate = StableCompletionGate(
        target_engagements=2,
        stable_seconds=4.0,
    )

    assert not recorder_should_stop(
        telemetry,
        {"cooling": 2, "relief": 1},
        completion_gate=gate,
        now=10.0,
    )
    assert not recorder_should_stop(
        telemetry,
        {"cooling": 2, "relief": 2},
        completion_gate=gate,
        now=11.0,
    )
    assert recorder_should_stop(
        telemetry,
        {"cooling": 2, "relief": 2},
        completion_gate=gate,
        now=15.0,
    )


def test_engagement_labels_show_independent_progress() -> None:
    labels = engagement_progress_labels(
        {
            "cooling_engagement_count": 1,
            "relief_engagement_count": 3,
            "engagement_target": 2,
        }
    )

    assert labels == ("COOLING 1/2", "RELIEF 2/2")


def test_valve_indicator_colors_distinguish_active_states() -> None:
    neutral = valve_indicator_color("cooling", False)

    assert valve_indicator_color("cooling", True) == (255, 196, 55)
    assert valve_indicator_color("relief", True) == (40, 180, 255)
    assert neutral == valve_indicator_color("relief", False)
    assert neutral != valve_indicator_color("cooling", True)
