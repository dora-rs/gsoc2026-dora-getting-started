from week11_runtime.observation_gate import (
    observer_is_docked,
    pressure_is_available,
)


def test_observation_gate_rejects_stale_pre_docking_messages() -> None:
    assert not observer_is_docked(
        {"location": "home", "docked": False}
    )
    assert not pressure_is_available(
        {"available": False, "value_kpa": None}
    )


def test_observation_gate_accepts_only_complete_docked_readings() -> None:
    assert observer_is_docked(
        {"location": "station", "docked": True}
    )
    assert pressure_is_available(
        {"available": True, "value_kpa": 188.2}
    )
    assert not pressure_is_available(
        {"available": True, "value_kpa": None}
    )
