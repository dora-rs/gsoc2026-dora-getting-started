from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_world_contains_two_role_specific_robots_and_process_devices() -> None:
    world = (ROOT / "worlds" / "week11_process_supervision.wbt").read_text(
        encoding="utf-8"
    )

    for required_def in (
        "OBSERVER_ROBOT",
        "OPERATOR_ROBOT",
        "TEMPERATURE_DISPLAY",
        "PRESSURE_DOCK",
        "COOLING_SWITCH_LEVER",
        "RELIEF_SWITCH_LEVER",
        "COOLING_INDICATOR",
        "RELIEF_INDICATOR",
    ):
        assert f"DEF {required_def} " in world

    assert world.count("controller \"week11_robot_controller\"") == 2
    assert 'name "Observer youBot"' in world
    assert 'name "Operator youBot"' in world
    assert 'controller "plant_display_controller"' in world


def test_observer_and_operator_topics_are_namespaced() -> None:
    controller = (
        ROOT
        / "controllers"
        / "week11_robot_controller"
        / "week11_robot_controller.py"
    ).read_text(encoding="utf-8")

    assert 'role = "observer"' in controller
    assert 'role = "operator"' in controller
    assert 'f"/week11/{self.role}/nav_command"' in controller
    assert '"/week11/operator/switch_event"' in controller
    assert '"/week11/observer/camera/image_raw"' in controller


def test_switch_motion_completes_within_predictive_control_window() -> None:
    controller = (
        ROOT
        / "controllers"
        / "week11_robot_controller"
        / "week11_robot_controller.py"
    ).read_text(encoding="utf-8")

    assert "ARM_ACTION_COMPLETE_SECONDS = 3.0" in controller
    assert "elapsed >= ARM_ACTION_COMPLETE_SECONDS" in controller


def test_location_config_keeps_roles_on_separate_routes() -> None:
    import json

    locations = json.loads(
        (ROOT / "config" / "week11_locations.json").read_text(
            encoding="utf-8"
        )
    )

    assert locations["observer_home"]["y"] > 0
    assert locations["observer_station"]["y"] > 0
    assert locations["operator_home"]["y"] < 0
    assert locations["control_station"]["y"] < 0
    assert locations["observer_station"]["x"] < locations["control_station"]["x"]
