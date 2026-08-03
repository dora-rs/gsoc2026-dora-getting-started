import pytest

from week11_runtime.contracts import (
    PressureReading,
    TemperatureObservation,
    build_process_snapshot,
)


def test_pressure_is_unavailable_until_observer_is_docked():
    reading = PressureReading.from_process(
        pressure_kpa=181.0,
        observed_at_s=10.0,
        observer_docked=False,
    )

    assert reading.available is False
    assert reading.value_kpa is None
    assert reading.error_code == "OBSERVER_NOT_DOCKED"


def test_snapshot_rejects_stale_temperature_observation():
    pressure = PressureReading.from_process(
        pressure_kpa=181.0,
        observed_at_s=10.0,
        observer_docked=True,
    )
    temperature = TemperatureObservation(
        value_c=52.0,
        confidence=0.94,
        frame_id="frame-001",
        observed_at_s=1.0,
    )

    with pytest.raises(ValueError, match="temperature observation is stale"):
        build_process_snapshot(
            sequence=4,
            now_s=10.0,
            pressure=pressure,
            temperature=temperature,
            cooling_on=False,
            relief_open=False,
            max_temperature_age_s=6.0,
        )


def test_snapshot_contains_only_observable_values_and_trends():
    pressure = PressureReading.from_process(
        pressure_kpa=191.0,
        observed_at_s=20.0,
        observer_docked=True,
    )
    temperature = TemperatureObservation(
        value_c=56.5,
        confidence=0.91,
        frame_id="frame-010",
        observed_at_s=19.0,
    )

    snapshot = build_process_snapshot(
        sequence=8,
        now_s=20.0,
        pressure=pressure,
        temperature=temperature,
        cooling_on=False,
        relief_open=False,
        previous_pressure_kpa=187.0,
        previous_temperature_c=55.0,
    )

    assert snapshot.sequence == 8
    assert snapshot.pressure.value_kpa == pytest.approx(191.0)
    assert snapshot.temperature.value_c == pytest.approx(56.5)
    assert snapshot.pressure_trend == "rising"
    assert snapshot.temperature_trend == "rising"
    assert not hasattr(snapshot, "ground_truth_temperature_c")
