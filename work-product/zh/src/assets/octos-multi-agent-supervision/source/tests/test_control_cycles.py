from week11_runtime.control_cycles import (
    ControlCycleTracker,
    ControlEngagementTracker,
    StableCompletionGate,
    cap_engagement_counts,
)


def telemetry(
    *,
    temperature_c: float = 50.0,
    pressure_kpa: float = 180.0,
    cooling_on: bool = False,
    relief_open: bool = False,
) -> dict:
    return {
        "temperature_c": temperature_c,
        "pressure_kpa": pressure_kpa,
        "cooling_on": cooling_on,
        "relief_open": relief_open,
        "temperature_safe_min_c": 30.0,
        "temperature_safe_max_c": 60.0,
        "pressure_safe_min_kpa": 160.0,
        "pressure_safe_max_kpa": 200.0,
    }


def test_passive_rise_does_not_start_a_control_cycle() -> None:
    tracker = ControlCycleTracker()

    assert tracker.update(telemetry()) == 0
    assert tracker.update(telemetry(temperature_c=56.0)) == 0


def test_safe_shutdown_completes_one_cycle_once() -> None:
    tracker = ControlCycleTracker()

    tracker.update(telemetry(cooling_on=True, relief_open=True))
    tracker.update(telemetry(cooling_on=True, relief_open=False))
    assert tracker.update(telemetry()) == 1
    assert tracker.update(telemetry()) == 1


def test_two_distinct_control_sequences_complete_two_cycles() -> None:
    tracker = ControlCycleTracker()

    tracker.update(telemetry(cooling_on=True))
    tracker.update(telemetry())
    tracker.update(telemetry(relief_open=True))

    assert tracker.update(telemetry()) == 2


def test_shutdown_outside_lower_range_does_not_complete_cycle() -> None:
    tracker = ControlCycleTracker()

    tracker.update(telemetry(cooling_on=True, relief_open=True))
    count = tracker.update(
        telemetry(temperature_c=29.9, pressure_kpa=159.9)
    )

    assert count == 0


def test_new_activation_after_invalid_shutdown_starts_a_fresh_cycle() -> None:
    tracker = ControlCycleTracker()

    tracker.update(telemetry(cooling_on=True))
    tracker.update(telemetry(temperature_c=29.0))
    tracker.update(telemetry(relief_open=True))

    assert tracker.update(telemetry()) == 1


def test_engagements_are_counted_independently() -> None:
    tracker = ControlEngagementTracker()

    tracker.update(telemetry(cooling_on=True))
    assert tracker.update(telemetry()) == {
        "cooling": 1,
        "relief": 0,
    }

    tracker.update(telemetry(relief_open=True))
    assert tracker.update(telemetry()) == {
        "cooling": 1,
        "relief": 1,
    }


def test_inactive_telemetry_does_not_double_count_engagements() -> None:
    tracker = ControlEngagementTracker()

    tracker.update(telemetry(cooling_on=True, relief_open=True))
    first_shutdown = tracker.update(telemetry())
    repeated_shutdown = tracker.update(telemetry())

    assert first_shutdown == {"cooling": 1, "relief": 1}
    assert repeated_shutdown == {"cooling": 1, "relief": 1}


def test_displayed_engagement_counts_are_capped_at_target() -> None:
    assert cap_engagement_counts(
        {"cooling": 2, "relief": 3},
        target=2,
    ) == {"cooling": 2, "relief": 2}


def test_unsafe_shutdown_does_not_count_an_engagement() -> None:
    tracker = ControlEngagementTracker()

    tracker.update(telemetry(cooling_on=True, relief_open=True))
    counts = tracker.update(
        telemetry(temperature_c=29.9, pressure_kpa=159.9)
    )

    assert counts == {"cooling": 0, "relief": 0}


def test_completion_gate_requires_both_targets_and_stable_safe_tail() -> None:
    gate = StableCompletionGate(
        target_engagements=2,
        stable_seconds=4.0,
    )
    safe = telemetry()

    assert not gate.update(
        safe,
        {"cooling": 2, "relief": 1},
        now=10.0,
    )
    assert not gate.update(
        safe,
        {"cooling": 2, "relief": 2},
        now=11.0,
    )
    assert not gate.update(
        safe,
        {"cooling": 2, "relief": 2},
        now=14.9,
    )
    assert gate.update(
        safe,
        {"cooling": 2, "relief": 2},
        now=15.0,
    )


def test_completion_gate_resets_when_safe_tail_is_interrupted() -> None:
    gate = StableCompletionGate(
        target_engagements=2,
        stable_seconds=4.0,
    )
    counts = {"cooling": 2, "relief": 2}

    assert not gate.update(telemetry(), counts, now=20.0)
    assert not gate.update(
        telemetry(cooling_on=True),
        counts,
        now=22.0,
    )
    assert not gate.update(telemetry(), counts, now=23.0)
    assert not gate.update(telemetry(), counts, now=26.9)
    assert gate.update(telemetry(), counts, now=27.0)
