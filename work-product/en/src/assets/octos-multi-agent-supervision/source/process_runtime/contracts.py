from dataclasses import dataclass


@dataclass(frozen=True)
class PressureReading:
    available: bool
    value_kpa: float | None
    observed_at_s: float
    error_code: str | None

    @classmethod
    def from_process(
        cls,
        *,
        pressure_kpa: float,
        observed_at_s: float,
        observer_docked: bool,
    ) -> "PressureReading":
        if not observer_docked:
            return cls(
                available=False,
                value_kpa=None,
                observed_at_s=observed_at_s,
                error_code="OBSERVER_NOT_DOCKED",
            )
        return cls(
            available=True,
            value_kpa=pressure_kpa,
            observed_at_s=observed_at_s,
            error_code=None,
        )


@dataclass(frozen=True)
class TemperatureObservation:
    value_c: float
    confidence: float
    frame_id: str
    observed_at_s: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")


@dataclass(frozen=True)
class ProcessSnapshot:
    sequence: int
    observed_at_s: float
    pressure: PressureReading
    temperature: TemperatureObservation
    cooling_on: bool
    relief_open: bool
    pressure_trend: str
    temperature_trend: str


def _trend(current: float, previous: float | None) -> str:
    if previous is None:
        return "unknown"
    delta = current - previous
    if delta > 0.1:
        return "rising"
    if delta < -0.1:
        return "falling"
    return "steady"


def build_process_snapshot(
    *,
    sequence: int,
    now_s: float,
    pressure: PressureReading,
    temperature: TemperatureObservation,
    cooling_on: bool,
    relief_open: bool,
    previous_pressure_kpa: float | None = None,
    previous_temperature_c: float | None = None,
    max_temperature_age_s: float = 6.0,
) -> ProcessSnapshot:
    if now_s - temperature.observed_at_s > max_temperature_age_s:
        raise ValueError("temperature observation is stale")

    pressure_value = pressure.value_kpa
    return ProcessSnapshot(
        sequence=sequence,
        observed_at_s=now_s,
        pressure=pressure,
        temperature=temperature,
        cooling_on=cooling_on,
        relief_open=relief_open,
        pressure_trend=(
            _trend(pressure_value, previous_pressure_kpa)
            if pressure_value is not None
            else "unavailable"
        ),
        temperature_trend=_trend(
            temperature.value_c,
            previous_temperature_c,
        ),
    )
