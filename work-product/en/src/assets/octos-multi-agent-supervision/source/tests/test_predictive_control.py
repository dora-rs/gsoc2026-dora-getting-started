import pytest

from process_runtime.predictive_control import (
    derive_process_metrics,
    project_value,
    seconds_to_limit,
)


def test_project_value_uses_rate_and_response_horizon() -> None:
    assert project_value(54.0, 0.2, 8.5) == pytest.approx(55.7)


def test_seconds_to_limit_returns_time_for_a_rising_signal() -> None:
    assert seconds_to_limit(57.0, 0.2, 60.0) == pytest.approx(15.0)


def test_seconds_to_limit_reports_zero_after_limit_is_reached() -> None:
    assert seconds_to_limit(61.0, 0.2, 60.0) == 0.0


def test_seconds_to_limit_is_unknown_for_a_non_rising_signal() -> None:
    assert seconds_to_limit(57.0, -0.3, 60.0) is None


def test_first_observation_uses_configured_process_rates() -> None:
    metrics = derive_process_metrics(
        {
            "temperature_c": 50.0,
            "pressure_kpa": 175.0,
            "pressure_observed_at_s": 10.0,
        },
        None,
        latency_seconds=5.0,
        fallback_temperature_rate=0.16,
        fallback_pressure_rate=0.4,
        switch_effect_delay_seconds=3.5,
    )

    assert metrics["temperature_rate_c_per_s"] == pytest.approx(0.16)
    assert metrics["pressure_rate_kpa_per_s"] == pytest.approx(0.4)
    assert metrics["response_horizon_seconds"] == pytest.approx(8.5)
    assert metrics["temperature_projected_at_response_c"] == pytest.approx(
        51.36
    )
    assert metrics["pressure_projected_at_response_kpa"] == pytest.approx(
        178.4
    )
    assert metrics["temperature_control_due"] is False
    assert metrics["pressure_control_due"] is False


def test_subsequent_observation_derives_rising_and_falling_rates() -> None:
    metrics = derive_process_metrics(
        {
            "temperature_c": 56.0,
            "pressure_kpa": 190.0,
            "pressure_observed_at_s": 20.0,
        },
        {
            "temperature_c": 58.0,
            "pressure_kpa": 185.0,
            "pressure_observed_at_s": 10.0,
        },
        latency_seconds=7.0,
    )

    assert metrics["temperature_rate_c_per_s"] == pytest.approx(-0.2)
    assert metrics["pressure_rate_kpa_per_s"] == pytest.approx(0.5)
    assert metrics["temperature_seconds_to_limit"] is None
    assert metrics["pressure_seconds_to_limit"] == pytest.approx(20.0)
    assert metrics["temperature_control_due"] is False
    assert metrics["pressure_control_due"] is True


def test_non_increasing_observation_timestamp_uses_fallback_rates() -> None:
    metrics = derive_process_metrics(
        {
            "temperature_c": 54.0,
            "pressure_kpa": 180.0,
            "pressure_observed_at_s": 10.0,
        },
        {
            "temperature_c": 53.0,
            "pressure_kpa": 179.0,
            "pressure_observed_at_s": 10.0,
        },
        latency_seconds=3.0,
        fallback_temperature_rate=0.16,
        fallback_pressure_rate=0.4,
    )

    assert metrics["temperature_rate_c_per_s"] == pytest.approx(0.16)
    assert metrics["pressure_rate_kpa_per_s"] == pytest.approx(0.4)


def test_control_is_due_before_waiting_through_another_observation_cycle() -> None:
    metrics = derive_process_metrics(
        {
            "temperature_c": 55.1,
            "pressure_kpa": 187.48,
            "pressure_observed_at_s": 31.2,
        },
        {
            "temperature_c": 50.1,
            "pressure_kpa": 175.0,
            "pressure_observed_at_s": 0.0,
        },
        latency_seconds=12.0,
        switch_effect_delay_seconds=3.5,
    )

    assert metrics["observation_cycle_seconds"] == pytest.approx(31.2)
    assert metrics["control_response_horizon_seconds"] == pytest.approx(15.5)
    assert metrics["wait_then_control_horizon_seconds"] == pytest.approx(46.7)
    assert metrics["temperature_projected_at_response_c"] == pytest.approx(
        57.583, abs=0.01
    )
    assert metrics["pressure_projected_at_response_kpa"] == pytest.approx(
        193.68, abs=0.01
    )
    assert metrics["temperature_projected_if_wait_c"] == pytest.approx(
        62.583, abs=0.01
    )
    assert metrics["pressure_projected_if_wait_kpa"] == pytest.approx(
        206.16, abs=0.01
    )
    assert metrics["temperature_control_due"] is True
    assert metrics["pressure_control_due"] is True


def test_shutdown_recommendation_targets_the_preferred_operating_band() -> None:
    metrics = derive_process_metrics(
        {
            "temperature_c": 59.7,
            "pressure_kpa": 198.744,
            "pressure_observed_at_s": 59.36,
        },
        {
            "temperature_c": 55.1,
            "pressure_kpa": 187.48,
            "pressure_observed_at_s": 31.2,
        },
        latency_seconds=12.0,
        switch_effect_delay_seconds=3.5,
    )

    assert metrics["temperature_recommended_disable_after_seconds"] == 18
    assert metrics["pressure_recommended_disable_after_seconds"] == 16
