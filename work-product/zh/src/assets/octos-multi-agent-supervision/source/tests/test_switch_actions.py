import pytest

from week11_runtime.switch_actions import execute_switch_actions_once


def test_independent_switch_actions_are_executed_once(tmp_path) -> None:
    calls: list[tuple[str, bool]] = []

    def set_switch(switch: str, enabled: bool) -> dict:
        calls.append((switch, enabled))
        return {
            "switch": switch,
            "enabled": enabled,
            "status": "succeeded",
        }

    arguments = {
        "action_id": "run-cycle-1-open",
        "actions": [
            {"switch": "cooling", "enabled": True},
            {"switch": "relief", "enabled": True},
        ],
        "current_state": {"cooling": False, "relief": False},
        "receipt_dir": tmp_path,
        "set_switch": set_switch,
    }

    first = execute_switch_actions_once(**arguments)
    second = execute_switch_actions_once(**arguments)

    assert calls == [("cooling", True), ("relief", True)]
    assert second == first
    assert first == {
        "action_id": "run-cycle-1-open",
        "events": [
            {
                "switch": "cooling",
                "enabled": True,
                "status": "succeeded",
            },
            {
                "switch": "relief",
                "enabled": True,
                "status": "succeeded",
            },
        ],
        "all_succeeded": True,
    }
    assert (tmp_path / "run-cycle-1-open.json").is_file()


@pytest.mark.parametrize(
    ("actions", "message"),
    [
        ([], "one or two"),
        (
            [
                {"switch": "cooling", "enabled": True},
                {"switch": "cooling", "enabled": False},
            ],
            "more than once",
        ),
        ([{"switch": "heater", "enabled": True}], "cooling or relief"),
        ([{"switch": "cooling", "enabled": "yes"}], "boolean"),
    ],
)
def test_switch_actions_reject_invalid_contract(
    tmp_path,
    actions: list[dict],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        execute_switch_actions_once(
            "run-invalid",
            actions,
            current_state={"cooling": False, "relief": False},
            receipt_dir=tmp_path,
            set_switch=lambda _switch, _enabled: {"status": "succeeded"},
        )


def test_switch_actions_treat_satisfied_state_as_idempotent_success(
    tmp_path,
) -> None:
    calls: list[tuple[str, bool]] = []

    result = execute_switch_actions_once(
        "run-repeat",
        [{"switch": "cooling", "enabled": True}],
        current_state={"cooling": True, "relief": False},
        receipt_dir=tmp_path,
        set_switch=lambda switch, enabled: calls.append((switch, enabled)),
    )

    assert calls == []
    assert result["all_succeeded"] is True
    assert result["events"] == [
        {
            "switch": "cooling",
            "enabled": True,
            "status": "already_satisfied",
        }
    ]


def test_failed_switch_action_does_not_write_success_receipt(tmp_path) -> None:
    with pytest.raises(RuntimeError, match="switch command failed"):
        execute_switch_actions_once(
            "run-failed",
            [{"switch": "relief", "enabled": True}],
            current_state={"cooling": False, "relief": False},
            receipt_dir=tmp_path,
            set_switch=lambda _switch, _enabled: {"status": "failed"},
        )

    assert not (tmp_path / "run-failed.json").exists()
