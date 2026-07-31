from dataclasses import dataclass


@dataclass(frozen=True)
class DisplayState:
    temperature_c: float
    pressure_kpa: float
    temperature_safe_min_c: float
    temperature_safe_max_c: float
    pressure_safe_min_kpa: float
    pressure_safe_max_kpa: float
    temperature_rate_c_per_s: float
    pressure_rate_kpa_per_s: float
    cooling_on: bool
    relief_open: bool
    observer_status: str
    operator_status: str
    agent_action: str
    cooling_engagement_count: int
    relief_engagement_count: int
    engagement_target: int


def gauge_fraction(value: float, *, minimum: float, maximum: float) -> float:
    if maximum <= minimum:
        raise ValueError("maximum must be greater than minimum")
    return max(0.0, min(1.0, (value - minimum) / (maximum - minimum)))


def gauge_fill_width(
    fraction: float, *, maximum_width: int
) -> int | None:
    width = int(maximum_width * max(0.0, min(1.0, fraction)))
    return width if width > 0 else None


def build_hud_lines(state: DisplayState) -> tuple[str, ...]:
    return (
        (
            f"TEMPERATURE  {state.temperature_c:.1f} C  SAFE "
            f"{state.temperature_safe_min_c:.0f}-"
            f"{state.temperature_safe_max_c:.0f} C  "
            f"{state.temperature_rate_c_per_s:+.2f} C/s"
        ),
        (
            f"PRESSURE     {state.pressure_kpa:.1f} kPa  SAFE "
            f"{state.pressure_safe_min_kpa:.0f}-"
            f"{state.pressure_safe_max_kpa:.0f} kPa  "
            f"{state.pressure_rate_kpa_per_s:+.2f} kPa/s"
        ),
        (
            f"COOLING {'ON' if state.cooling_on else 'OFF'}    "
            f"RELIEF {'OPEN' if state.relief_open else 'CLOSED'}"
        ),
        (
            f"OBSERVER {state.observer_status}    "
            f"OPERATOR {state.operator_status}    "
            f"COOLING {state.cooling_engagement_count}/"
            f"{state.engagement_target}    "
            f"RELIEF {state.relief_engagement_count}/"
            f"{state.engagement_target}"
        ),
        f"OCTOS  {state.agent_action}",
    )
