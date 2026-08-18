from __future__ import annotations

import math
from typing import Any


def project_value(
    value: float, rate_per_second: float, horizon_seconds: float
) -> float:
    return float(value) + float(rate_per_second) * float(horizon_seconds)


def seconds_to_limit(
    value: float, rate_per_second: float, limit: float
) -> float | None:
    value = float(value)
    rate_per_second = float(rate_per_second)
    limit = float(limit)
    if value >= limit:
        return 0.0
    if rate_per_second <= 0.0:
        return None
    return (limit - value) / rate_per_second


def _observation_time(observation: dict[str, Any]) -> float:
    return float(
        observation.get(
            "pressure_observed_at_s",
            observation.get("observed_at_s", 0.0),
        )
    )


def _observed_rate(
    current: dict[str, Any],
    previous: dict[str, Any] | None,
    *,
    field: str,
    fallback: float,
) -> float:
    if previous is None:
        return float(fallback)
    elapsed = _observation_time(current) - _observation_time(previous)
    if elapsed <= 0.0:
        return float(fallback)
    return (
        float(current[field]) - float(previous[field])
    ) / elapsed


def _observation_cycle_seconds(
    current: dict[str, Any],
    previous: dict[str, Any] | None,
    fallback: float,
) -> float:
    if previous is None:
        return float(fallback)
    elapsed = _observation_time(current) - _observation_time(previous)
    return elapsed if elapsed > 0.0 else float(fallback)


def _recommended_disable_after_seconds(
    projected_value: float,
    target_value: float,
    control_rate_per_second: float,
    active_overhead_seconds: float,
) -> int:
    if control_rate_per_second >= 0.0:
        raise ValueError("control rate must be negative")
    active_seconds = max(
        0.0,
        (float(projected_value) - float(target_value))
        / abs(float(control_rate_per_second)),
    )
    requested = math.ceil(active_seconds - float(active_overhead_seconds))
    return max(2, min(30, requested))


def derive_process_metrics(
    current: dict[str, Any],
    previous: dict[str, Any] | None,
    *,
    latency_seconds: float,
    fallback_temperature_rate: float = 0.16,
    fallback_pressure_rate: float = 0.4,
    switch_effect_delay_seconds: float = 3.5,
    fallback_observation_cycle_seconds: float = 30.0,
    cooling_net_rate_c_per_s: float = -0.30,
    relief_net_rate_kpa_per_s: float = -0.80,
    switch_active_overhead_seconds: float = 3.0,
) -> dict[str, float | int | bool | None]:
    temperature = float(current["temperature_c"])
    pressure = float(current["pressure_kpa"])
    temperature_rate = _observed_rate(
        current,
        previous,
        field="temperature_c",
        fallback=fallback_temperature_rate,
    )
    pressure_rate = _observed_rate(
        current,
        previous,
        field="pressure_kpa",
        fallback=fallback_pressure_rate,
    )
    observation_cycle = _observation_cycle_seconds(
        current,
        previous,
        fallback_observation_cycle_seconds,
    )
    control_response_horizon = (
        float(latency_seconds) + float(switch_effect_delay_seconds)
    )
    wait_then_control_horizon = (
        observation_cycle + control_response_horizon
    )
    projected_temperature = project_value(
        temperature, temperature_rate, control_response_horizon
    )
    projected_pressure = project_value(
        pressure, pressure_rate, control_response_horizon
    )
    projected_temperature_if_wait = project_value(
        temperature, temperature_rate, wait_then_control_horizon
    )
    projected_pressure_if_wait = project_value(
        pressure, pressure_rate, wait_then_control_horizon
    )
    return {
        "temperature_rate_c_per_s": temperature_rate,
        "pressure_rate_kpa_per_s": pressure_rate,
        "temperature_projected_at_response_c": projected_temperature,
        "pressure_projected_at_response_kpa": projected_pressure,
        "temperature_projected_if_wait_c": projected_temperature_if_wait,
        "pressure_projected_if_wait_kpa": projected_pressure_if_wait,
        "temperature_seconds_to_limit": seconds_to_limit(
            temperature, temperature_rate, 60.0
        ),
        "pressure_seconds_to_limit": seconds_to_limit(
            pressure, pressure_rate, 200.0
        ),
        "observation_cycle_seconds": observation_cycle,
        "control_response_horizon_seconds": control_response_horizon,
        "wait_then_control_horizon_seconds": wait_then_control_horizon,
        "response_horizon_seconds": control_response_horizon,
        "cooling_net_rate_c_per_s": cooling_net_rate_c_per_s,
        "relief_net_rate_kpa_per_s": relief_net_rate_kpa_per_s,
        "switch_active_overhead_seconds": switch_active_overhead_seconds,
        "temperature_recommended_disable_after_seconds":
            _recommended_disable_after_seconds(
                projected_temperature,
                56.0,
                cooling_net_rate_c_per_s,
                switch_active_overhead_seconds,
            ),
        "pressure_recommended_disable_after_seconds":
            _recommended_disable_after_seconds(
                projected_pressure,
                190.0,
                relief_net_rate_kpa_per_s,
                switch_active_overhead_seconds,
            ),
        "temperature_control_due": projected_temperature_if_wait >= 58.0,
        "pressure_control_due": projected_pressure_if_wait >= 195.0,
    }
