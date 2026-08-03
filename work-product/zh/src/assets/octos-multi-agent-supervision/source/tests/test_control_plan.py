import pytest

from week11_runtime.control_plan import (
    execute_control_plan,
    execute_control_plan_once,
)


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


def test_control_plan_disables_each_switch_at_its_own_due_time() -> None:
    clock = FakeClock()
    events: list[tuple[str, bool, float]] = []

    def set_switch(switch: str, enabled: bool) -> dict:
        clock.now += 1.0
        events.append((switch, enabled, clock.now))
        return {"switch": switch, "enabled": enabled, "status": "succeeded"}

    result = execute_control_plan(
        [
            {"switch": "cooling", "disable_after_seconds": 12},
            {"switch": "relief", "disable_after_seconds": 8},
        ],
        set_switch=set_switch,
        sleep=clock.sleep,
        monotonic=clock.monotonic,
    )

    assert events == [
        ("cooling", True, 1.0),
        ("relief", True, 2.0),
        ("relief", False, 11.0),
        ("cooling", False, 14.0),
    ]
    assert result["all_succeeded"] is True
    assert result["elapsed_seconds"] == pytest.approx(14.0)


def test_control_plan_sorts_shutdowns_by_due_time_not_input_order() -> None:
    clock = FakeClock()
    disabled: list[str] = []

    def set_switch(switch: str, enabled: bool) -> dict:
        if not enabled:
            disabled.append(switch)
        return {"status": "succeeded"}

    execute_control_plan(
        [
            {"switch": "cooling", "disable_after_seconds": 20},
            {"switch": "relief", "disable_after_seconds": 5},
        ],
        set_switch=set_switch,
        sleep=clock.sleep,
        monotonic=clock.monotonic,
    )

    assert disabled == ["relief", "cooling"]


@pytest.mark.parametrize(
    "plans, message",
    [
        ([], "one or two"),
        (
            [
                {"switch": "cooling", "disable_after_seconds": 8},
                {"switch": "cooling", "disable_after_seconds": 10},
            ],
            "more than once",
        ),
        (
            [{"switch": "heater", "disable_after_seconds": 8}],
            "cooling or relief",
        ),
        (
            [{"switch": "cooling", "disable_after_seconds": 31}],
            "2 and 30",
        ),
    ],
)
def test_control_plan_rejects_invalid_plans(
    plans: list[dict], message: str
) -> None:
    clock = FakeClock()

    with pytest.raises(ValueError, match=message):
        execute_control_plan(
            plans,
            set_switch=lambda _switch, _enabled: {"status": "succeeded"},
            sleep=clock.sleep,
            monotonic=clock.monotonic,
        )


def test_control_plan_stops_after_a_failed_switch_command() -> None:
    clock = FakeClock()

    def set_switch(_switch: str, _enabled: bool) -> dict:
        return {"status": "failed"}

    with pytest.raises(RuntimeError, match="switch command failed"):
        execute_control_plan(
            [{"switch": "cooling", "disable_after_seconds": 8}],
            set_switch=set_switch,
            sleep=clock.sleep,
            monotonic=clock.monotonic,
        )


def test_repeated_plan_id_returns_receipt_without_repeating_actions(
    tmp_path,
) -> None:
    clock = FakeClock()
    events: list[tuple[str, bool]] = []

    def set_switch(switch: str, enabled: bool) -> dict:
        events.append((switch, enabled))
        clock.now += 1.0
        return {"status": "succeeded"}

    arguments = {
        "plan_id": "mission-round-2",
        "plans": [
            {"switch": "cooling", "disable_after_seconds": 3},
            {"switch": "relief", "disable_after_seconds": 2},
        ],
        "receipt_dir": tmp_path,
        "set_switch": set_switch,
        "sleep": clock.sleep,
        "monotonic": clock.monotonic,
    }

    first = execute_control_plan_once(**arguments)
    second = execute_control_plan_once(**arguments)

    assert events == [
        ("cooling", True),
        ("relief", True),
        ("cooling", False),
        ("relief", False),
    ]
    assert second == first
    assert second["plan_id"] == "mission-round-2"
    assert (tmp_path / "mission-round-2.json").is_file()
