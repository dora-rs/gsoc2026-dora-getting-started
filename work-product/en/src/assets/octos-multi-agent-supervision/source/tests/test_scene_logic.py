import pytest

from process_runtime.scene_logic import (
    ControlStation,
    Pose2D,
    SwitchPanel,
    is_observer_docked,
    should_start_process,
)


def test_observer_docking_requires_position_and_heading() -> None:
    station = Pose2D(x=-2.6, y=1.2, heading_deg=90.0)

    assert is_observer_docked(
        Pose2D(x=-2.55, y=1.16, heading_deg=93.0),
        station,
    )
    assert not is_observer_docked(
        Pose2D(x=-2.2, y=1.2, heading_deg=90.0),
        station,
    )
    assert not is_observer_docked(
        Pose2D(x=-2.55, y=1.16, heading_deg=125.0),
        station,
    )


def test_switch_panel_rejects_actions_away_from_control_station() -> None:
    panel = SwitchPanel()
    station = ControlStation(Pose2D(x=2.4, y=1.0, heading_deg=-90.0))

    with pytest.raises(PermissionError, match="not at the control station"):
        panel.apply(
            switch_name="cooling",
            enabled=True,
            robot_pose=Pose2D(x=0.0, y=0.0, heading_deg=0.0),
            arm_pose_name="press_cooling",
            station=station,
        )


def test_switch_panel_requires_matching_verified_arm_pose() -> None:
    panel = SwitchPanel()
    station = ControlStation(Pose2D(x=2.4, y=1.0, heading_deg=-90.0))
    robot_pose = Pose2D(x=2.43, y=1.03, heading_deg=-88.0)

    with pytest.raises(ValueError, match="verified arm pose"):
        panel.apply(
            switch_name="relief",
            enabled=True,
            robot_pose=robot_pose,
            arm_pose_name="press_cooling",
            station=station,
        )

    state = panel.apply(
        switch_name="relief",
        enabled=True,
        robot_pose=robot_pose,
        arm_pose_name="press_relief",
        station=station,
    )
    assert state.relief_open
    assert not state.cooling_on


def test_unknown_switch_is_rejected() -> None:
    panel = SwitchPanel()
    station = ControlStation(Pose2D(x=2.4, y=1.0, heading_deg=-90.0))

    with pytest.raises(ValueError, match="unknown switch"):
        panel.apply(
            switch_name="alarm",
            enabled=True,
            robot_pose=station.pose,
            arm_pose_name="press_alarm",
            station=station,
        )


def test_process_start_is_not_gated_by_robot_readiness() -> None:
    assert should_start_process(
        phase="idle",
        observer_docked=False,
        operator_at_control=False,
    )
    assert should_start_process(
        phase="idle",
        observer_docked=True,
        operator_at_control=True,
    )
    assert not should_start_process(
        phase="running",
        observer_docked=False,
        operator_at_control=False,
    )
