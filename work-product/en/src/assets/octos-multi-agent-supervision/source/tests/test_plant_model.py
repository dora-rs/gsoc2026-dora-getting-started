import pytest

from process_runtime.plant_model import (
    PlantConfig,
    PlantModel,
    plant_config_from_environment,
)


def test_process_starts_from_configured_values():
    model = PlantModel(PlantConfig())

    state = model.state

    assert state.temperature_c == pytest.approx(32.0)
    assert state.pressure_kpa == pytest.approx(162.0)
    assert state.phase == "idle"


def test_started_process_heats_and_pressurizes_at_configured_rates():
    model = PlantModel(PlantConfig())
    model.start()

    state = model.step(10.0)

    assert state.temperature_c == pytest.approx(34.5)
    assert state.pressure_kpa == pytest.approx(165.2)
    assert state.phase == "running"


def test_cooling_and_relief_reverse_the_process_trends():
    model = PlantModel(
        PlantConfig(
            initial_temperature_c=42.0,
            initial_pressure_kpa=165.0,
        )
    )
    model.start()
    model.set_cooling(True)
    model.set_relief(True)

    state = model.step(1.0)

    assert state.temperature_c == pytest.approx(40.9)
    assert state.pressure_kpa == pytest.approx(161.82)
    assert state.cooling_on is True
    assert state.relief_open is True


def test_default_normal_ranges_include_lower_and_upper_limits():
    config = PlantConfig()

    assert (
        config.temperature_safe_min_c,
        config.temperature_safe_max_c,
    ) == (30.0, 60.0)
    assert (
        config.pressure_safe_min_kpa,
        config.pressure_safe_max_kpa,
    ) == (160.0, 200.0)


def test_lower_safety_bound_clamps_values_and_turns_controls_off():
    model = PlantModel(
        PlantConfig(
            initial_temperature_c=30.1,
            initial_pressure_kpa=160.2,
        )
    )
    model.start()
    model.set_cooling(True)
    model.set_relief(True)

    state = model.step(1.0)

    assert state.temperature_c == pytest.approx(30.0)
    assert state.pressure_kpa == pytest.approx(160.0)
    assert state.cooling_on is False
    assert state.relief_open is False


def test_hard_limit_trips_emergency_and_stops_further_rise():
    config = PlantConfig(
        initial_temperature_c=69.7,
        initial_pressure_kpa=229.5,
    )
    model = PlantModel(config)
    model.start()

    tripped = model.step(2.0)
    after_trip = model.step(10.0)

    assert tripped.phase == "emergency"
    assert tripped.emergency_reason == "temperature_and_pressure_hard_limit"
    assert after_trip.temperature_c == pytest.approx(tripped.temperature_c)
    assert after_trip.pressure_kpa == pytest.approx(tripped.pressure_kpa)


def test_step_rejects_non_positive_elapsed_time():
    model = PlantModel(PlantConfig())

    with pytest.raises(ValueError, match="dt_seconds must be positive"):
        model.step(0.0)


def test_completed_process_freezes_verified_values_with_controls_off():
    model = PlantModel(PlantConfig())
    model.start()
    model.step(10.0)
    model.set_cooling(True)
    model.set_relief(True)

    completed = model.complete()
    after_completion = model.step(10.0)

    assert completed.phase == "completed"
    assert completed.cooling_on is False
    assert completed.relief_open is False
    assert after_completion.temperature_c == pytest.approx(
        completed.temperature_c
    )
    assert after_completion.pressure_kpa == pytest.approx(
        completed.pressure_kpa
    )


def test_environment_can_slow_pressure_for_agent_observation_cycles():
    config = plant_config_from_environment(
        {
            "PROCESS_INITIAL_TEMPERATURE_C": "50.0",
            "PROCESS_INITIAL_PRESSURE_KPA": "170.0",
            "PROCESS_HEATING_RATE_C_PER_S": "0.18",
            "PROCESS_PRESSURE_RATE_KPA_PER_S": "0.5",
            "PROCESS_COOLING_EFFECT_C_PER_S": "-0.46",
            "PROCESS_RELIEF_EFFECT_KPA_PER_S": "-1.2",
        }
    )

    assert config.initial_temperature_c == 50.0
    assert config.initial_pressure_kpa == 170.0
    assert config.heating_rate_c_per_s == 0.18
    assert config.pressure_rate_kpa_per_s == 0.5
    assert config.cooling_effect_c_per_s == -0.46
    assert config.relief_effect_kpa_per_s == -1.2
