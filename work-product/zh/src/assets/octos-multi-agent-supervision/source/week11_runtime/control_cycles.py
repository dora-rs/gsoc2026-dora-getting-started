from __future__ import annotations


def inside_normal_ranges(telemetry: dict) -> bool:
    return (
        float(telemetry["temperature_safe_min_c"])
        <= float(telemetry["temperature_c"])
        <= float(telemetry["temperature_safe_max_c"])
        and float(telemetry["pressure_safe_min_kpa"])
        <= float(telemetry["pressure_kpa"])
        <= float(telemetry["pressure_safe_max_kpa"])
    )


def cap_engagement_counts(
    counts: dict[str, int],
    *,
    target: int,
) -> dict[str, int]:
    return {
        control: min(int(counts.get(control, 0)), target)
        for control in ("cooling", "relief")
    }


class ControlCycleTracker:
    def __init__(self) -> None:
        self.count = 0
        self._active_cycle = False
        self._controls_were_active = False

    @staticmethod
    def _inside_normal_ranges(telemetry: dict) -> bool:
        return inside_normal_ranges(telemetry)

    def update(self, telemetry: dict) -> int:
        controls_active = bool(
            telemetry.get("cooling_on") or telemetry.get("relief_open")
        )
        if controls_active:
            self._active_cycle = True
            self._controls_were_active = True
            return self.count

        if self._active_cycle and self._controls_were_active:
            if self._inside_normal_ranges(telemetry):
                self.count += 1
            self._active_cycle = False
            self._controls_were_active = False
        return self.count


class ControlEngagementTracker:
    FIELDS = {
        "cooling": "cooling_on",
        "relief": "relief_open",
    }

    def __init__(self) -> None:
        self.counts = {"cooling": 0, "relief": 0}
        self._was_active = {"cooling": False, "relief": False}

    def update(self, telemetry: dict) -> dict[str, int]:
        safe = inside_normal_ranges(telemetry)
        for control, field in self.FIELDS.items():
            active = bool(telemetry.get(field))
            if active:
                self._was_active[control] = True
            elif self._was_active[control]:
                if safe:
                    self.counts[control] += 1
                self._was_active[control] = False
        return dict(self.counts)


class StableCompletionGate:
    def __init__(
        self,
        *,
        target_engagements: int,
        stable_seconds: float,
    ) -> None:
        if target_engagements < 1:
            raise ValueError("target_engagements must be positive")
        if stable_seconds < 0:
            raise ValueError("stable_seconds cannot be negative")
        self.target_engagements = target_engagements
        self.stable_seconds = stable_seconds
        self._safe_since: float | None = None

    def update(
        self,
        telemetry: dict,
        counts: dict[str, int],
        *,
        now: float,
    ) -> bool:
        target_reached = all(
            int(counts[control]) >= self.target_engagements
            for control in ("cooling", "relief")
        )
        controls_off = not bool(
            telemetry.get("cooling_on") or telemetry.get("relief_open")
        )
        eligible = (
            target_reached
            and controls_off
            and inside_normal_ranges(telemetry)
        )
        if not eligible:
            self._safe_since = None
            return False
        if self._safe_since is None or now < self._safe_since:
            self._safe_since = now
        return now - self._safe_since >= self.stable_seconds
