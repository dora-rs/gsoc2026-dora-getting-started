from dataclasses import dataclass, replace
from typing import Mapping


@dataclass(frozen=True)
class PlantConfig:
    initial_temperature_c: float = 32.0
    initial_pressure_kpa: float = 162.0
    heating_rate_c_per_s: float = 0.25
    pressure_rate_kpa_per_s: float = 0.32
    cooling_effect_c_per_s: float = -1.35
    relief_effect_kpa_per_s: float = -3.50
    temperature_safe_min_c: float = 30.0
    temperature_safe_max_c: float = 60.0
    pressure_safe_min_kpa: float = 160.0
    pressure_safe_max_kpa: float = 200.0
    temperature_hard_min_c: float = 25.0
    temperature_hard_max_c: float = 70.0
    pressure_hard_min_kpa: float = 145.0
    pressure_hard_max_kpa: float = 230.0


@dataclass(frozen=True)
class PlantState:
    elapsed_s: float
    temperature_c: float
    pressure_kpa: float
    cooling_on: bool
    relief_open: bool
    phase: str
    emergency_reason: str | None = None


def plant_config_from_environment(
    environment: Mapping[str, str],
) -> PlantConfig:
    return PlantConfig(
        initial_temperature_c=float(
            environment.get("WEEK11_INITIAL_TEMPERATURE_C", "32.0")
        ),
        initial_pressure_kpa=float(
            environment.get("WEEK11_INITIAL_PRESSURE_KPA", "162.0")
        ),
        heating_rate_c_per_s=float(
            environment.get("WEEK11_HEATING_RATE_C_PER_S", "0.25")
        ),
        pressure_rate_kpa_per_s=float(
            environment.get("WEEK11_PRESSURE_RATE_KPA_PER_S", "0.32")
        ),
        cooling_effect_c_per_s=float(
            environment.get("WEEK11_COOLING_EFFECT_C_PER_S", "-1.35")
        ),
        relief_effect_kpa_per_s=float(
            environment.get("WEEK11_RELIEF_EFFECT_KPA_PER_S", "-3.50")
        ),
    )


class PlantModel:
    def __init__(self, config: PlantConfig):
        self.config = config
        self._state = PlantState(
            elapsed_s=0.0,
            temperature_c=config.initial_temperature_c,
            pressure_kpa=config.initial_pressure_kpa,
            cooling_on=False,
            relief_open=False,
            phase="idle",
        )

    @property
    def state(self) -> PlantState:
        return self._state

    def start(self) -> PlantState:
        if self._state.phase == "idle":
            self._state = replace(self._state, phase="running")
        return self._state

    def set_cooling(self, enabled: bool) -> PlantState:
        self._state = replace(self._state, cooling_on=enabled)
        return self._state

    def set_relief(self, enabled: bool) -> PlantState:
        self._state = replace(self._state, relief_open=enabled)
        return self._state

    def complete(self) -> PlantState:
        self._state = replace(
            self._state,
            cooling_on=False,
            relief_open=False,
            phase="completed",
        )
        return self._state

    def step(self, dt_seconds: float) -> PlantState:
        if dt_seconds <= 0:
            raise ValueError("dt_seconds must be positive")
        if self._state.phase != "running":
            return self._state

        temperature_rate = self.config.heating_rate_c_per_s
        if self._state.cooling_on:
            temperature_rate += self.config.cooling_effect_c_per_s

        pressure_rate = self.config.pressure_rate_kpa_per_s
        if self._state.relief_open:
            pressure_rate += self.config.relief_effect_kpa_per_s

        next_state = replace(
            self._state,
            elapsed_s=self._state.elapsed_s + dt_seconds,
            temperature_c=self._state.temperature_c
            + temperature_rate * dt_seconds,
            pressure_kpa=self._state.pressure_kpa
            + pressure_rate * dt_seconds,
        )

        if (
            next_state.cooling_on
            and next_state.temperature_c <= self.config.temperature_safe_min_c
        ):
            next_state = replace(
                next_state,
                temperature_c=self.config.temperature_safe_min_c,
                cooling_on=False,
            )
        if (
            next_state.relief_open
            and next_state.pressure_kpa <= self.config.pressure_safe_min_kpa
        ):
            next_state = replace(
                next_state,
                pressure_kpa=self.config.pressure_safe_min_kpa,
                relief_open=False,
            )

        temperature_tripped = (
            next_state.temperature_c >= self.config.temperature_hard_max_c
        )
        pressure_tripped = (
            next_state.pressure_kpa >= self.config.pressure_hard_max_kpa
        )
        if temperature_tripped or pressure_tripped:
            if temperature_tripped and pressure_tripped:
                reason = "temperature_and_pressure_hard_limit"
            elif temperature_tripped:
                reason = "temperature_hard_limit"
            else:
                reason = "pressure_hard_limit"
            next_state = replace(
                next_state,
                cooling_on=True,
                relief_open=True,
                phase="emergency",
                emergency_reason=reason,
            )

        self._state = next_state
        return self._state
