import pytest

from week11_runtime.octos_protocol import (
    parse_strategy_proposal,
    parse_octos_chat_response,
    parse_supervisor_decision,
    validate_predictive_decision,
)


def test_strategy_proposal_extracts_python_source() -> None:
    proposal = parse_strategy_proposal(
        """
        {
          "strategy_source": "def decide(context):\\n    return {}\\n",
          "reason": "initial adaptive policy"
        }
        """
    )

    assert proposal.source.startswith("def decide(context):")
    assert proposal.reason == "initial adaptive policy"


def test_strategy_proposal_requires_source_and_reason() -> None:
    with pytest.raises(ValueError, match="strategy_source"):
        parse_strategy_proposal('{"reason":"missing source"}')


def predictive_decision_json(
    *,
    actions_now: str = "[]",
    scheduled_actions: str = "[]",
    interval: int = 4,
    done: str = "false",
) -> str:
    return (
        f'{{"actions_now":{actions_now},'
        f'"scheduled_actions":{scheduled_actions},'
        f'"next_observation_seconds":{interval},'
        f'"done":{done},"reason":"rate-aware decision"}}'
    )


def test_supervisor_decision_accepts_a_scheduled_predictive_plan() -> None:
    decision = parse_supervisor_decision(
        predictive_decision_json(
            actions_now=(
                '[{"switch":"cooling","enabled":true},'
                '{"switch":"relief","enabled":true}]'
            ),
            scheduled_actions=(
                '[{"switch":"relief","enabled":false,"after_seconds":8},'
                '{"switch":"cooling","enabled":false,"after_seconds":12}]'
            ),
            interval=3,
        )
    )

    assert decision.actions_now[0].switch == "cooling"
    assert decision.scheduled_actions[0].after_seconds == 8
    assert decision.next_observation_seconds == 3
    assert not decision.done


def test_predictive_contract_allows_action_before_normal_limit() -> None:
    decision = parse_supervisor_decision(
        predictive_decision_json(
            actions_now='[{"switch":"relief","enabled":true}]',
            scheduled_actions=(
                '[{"switch":"relief","enabled":false,"after_seconds":10}]'
            ),
        )
    )

    validate_predictive_decision(
        decision,
        {"cooling": False, "relief": False},
        {"temperature_c": 56.0, "pressure_kpa": 190.0},
        round_number=1,
        post_action_observation=False,
        metrics={
            "temperature_projected_at_response_c": 56.5,
            "pressure_projected_at_response_kpa": 196.0,
        },
    )


def test_predictive_contract_rejects_action_far_before_response_window() -> None:
    decision = parse_supervisor_decision(
        predictive_decision_json(
            actions_now='[{"switch":"relief","enabled":true}]',
            scheduled_actions=(
                '[{"switch":"relief","enabled":false,"after_seconds":8}]'
            ),
        )
    )

    with pytest.raises(ValueError, match="too early"):
        validate_predictive_decision(
            decision,
            {"cooling": False, "relief": False},
            {"temperature_c": 50.2, "pressure_kpa": 175.0},
            round_number=1,
            post_action_observation=False,
            metrics={
                "temperature_projected_at_response_c": 52.68,
                "pressure_projected_at_response_kpa": 181.2,
            },
        )


def test_predictive_contract_requires_control_before_projected_boundary() -> None:
    decision = parse_supervisor_decision(
        predictive_decision_json()
    )

    with pytest.raises(ValueError, match="relief must be enabled"):
        validate_predictive_decision(
            decision,
            {"cooling": False, "relief": False},
            {"temperature_c": 56.8, "pressure_kpa": 190.0},
            round_number=2,
            post_action_observation=False,
            metrics={
                "temperature_projected_at_response_c": 57.5,
                "pressure_projected_at_response_kpa": 196.2,
            },
        )


def test_predictive_contract_rejects_shutdown_that_stays_above_operating_band() -> None:
    decision = parse_supervisor_decision(
        predictive_decision_json(
            actions_now=(
                '[{"switch":"cooling","enabled":true},'
                '{"switch":"relief","enabled":true}]'
            ),
            scheduled_actions=(
                '[{"switch":"cooling","enabled":false,"after_seconds":2},'
                '{"switch":"relief","enabled":false,"after_seconds":2}]'
            ),
        )
    )

    with pytest.raises(ValueError, match="shutdown remains above"):
        validate_predictive_decision(
            decision,
            {"cooling": False, "relief": False},
            {"temperature_c": 59.7, "pressure_kpa": 198.744},
            round_number=3,
            post_action_observation=False,
            metrics={
                "temperature_projected_if_wait_c": 66.7,
                "pressure_projected_if_wait_kpa": 216.2,
                "temperature_projected_at_response_c": 62.18,
                "pressure_projected_at_response_kpa": 204.94,
                "temperature_control_due": True,
                "pressure_control_due": True,
                "cooling_net_rate_c_per_s": -0.30,
                "relief_net_rate_kpa_per_s": -0.80,
                "switch_active_overhead_seconds": 3.0,
            },
        )


def test_predictive_contract_requires_shutdown_for_newly_enabled_switch() -> None:
    decision = parse_supervisor_decision(
        predictive_decision_json(
            actions_now='[{"switch":"cooling","enabled":true}]'
        )
    )

    with pytest.raises(ValueError, match="scheduled shutdown"):
        validate_predictive_decision(
            decision,
            {"cooling": False, "relief": False},
            {"temperature_c": 56.0, "pressure_kpa": 180.0},
            round_number=1,
            post_action_observation=False,
        )


def test_predictive_contract_rejects_schedule_for_inactive_switch() -> None:
    decision = parse_supervisor_decision(
        predictive_decision_json(
            scheduled_actions=(
                '[{"switch":"relief","enabled":false,"after_seconds":8}]'
            )
        )
    )

    with pytest.raises(ValueError, match="not active"):
        validate_predictive_decision(
            decision,
            {"cooling": False, "relief": False},
            {"temperature_c": 54.0, "pressure_kpa": 180.0},
            round_number=1,
            post_action_observation=False,
        )


def test_predictive_contract_rejects_an_immediate_no_op() -> None:
    decision = parse_supervisor_decision(
        predictive_decision_json(
            actions_now='[{"switch":"cooling","enabled":true}]',
            scheduled_actions=(
                '[{"switch":"cooling","enabled":false,"after_seconds":8}]'
            ),
        )
    )

    with pytest.raises(ValueError, match="already true"):
        validate_predictive_decision(
            decision,
            {"cooling": True, "relief": False},
            {"temperature_c": 56.0, "pressure_kpa": 180.0},
            round_number=2,
            post_action_observation=True,
        )


def test_supervisor_decision_rejects_out_of_range_schedule() -> None:
    with pytest.raises(ValueError, match="2 and 30"):
        parse_supervisor_decision(
            predictive_decision_json(
                scheduled_actions=(
                    '[{"switch":"cooling","enabled":false,'
                    '"after_seconds":31}]'
                )
            )
        )


def test_supervisor_decision_rejects_out_of_range_interval() -> None:
    with pytest.raises(ValueError, match="2 and 12"):
        parse_supervisor_decision(
            predictive_decision_json(interval=20)
        )


def test_supervisor_decision_rejects_unknown_action() -> None:
    with pytest.raises(ValueError, match="switch"):
        parse_supervisor_decision(
            predictive_decision_json(
                actions_now='[{"switch":"heater","enabled":true}]'
            )
        )


def test_completion_requires_post_action_safe_observation_and_controls_off() -> None:
    decision = parse_supervisor_decision(
        predictive_decision_json(done="true")
    )

    with pytest.raises(ValueError, match="before completion"):
        validate_predictive_decision(
            decision,
            {"cooling": False, "relief": False},
            {"temperature_c": 56.0, "pressure_kpa": 190.0},
            round_number=1,
            post_action_observation=False,
        )

    validate_predictive_decision(
        decision,
        {"cooling": False, "relief": False},
        {"temperature_c": 56.0, "pressure_kpa": 190.0},
        round_number=2,
        post_action_observation=True,
    )


def test_safe_post_action_observation_finishes_before_future_projection() -> None:
    decision = parse_supervisor_decision(
        predictive_decision_json(done="true")
    )

    validate_predictive_decision(
        decision,
        {"cooling": False, "relief": False},
        {"temperature_c": 59.2, "pressure_kpa": 197.0},
        round_number=3,
        post_action_observation=True,
        metrics={
            "temperature_projected_at_response_c": 60.6,
            "pressure_projected_at_response_kpa": 200.4,
            "temperature_projected_if_wait_c": 65.1,
            "pressure_projected_if_wait_kpa": 211.3,
            "temperature_control_due": True,
            "pressure_control_due": True,
        },
    )


def test_safe_post_action_observation_rejects_another_control_cycle() -> None:
    decision = parse_supervisor_decision(
        predictive_decision_json(
            actions_now='[{"switch":"cooling","enabled":true}]',
            scheduled_actions=(
                '[{"switch":"cooling","enabled":false,"after_seconds":8}]'
            ),
        )
    )

    with pytest.raises(ValueError, match="requires done=true"):
        validate_predictive_decision(
            decision,
            {"cooling": False, "relief": False},
            {"temperature_c": 59.2, "pressure_kpa": 197.0},
            round_number=3,
            post_action_observation=True,
            metrics={
                "temperature_projected_at_response_c": 60.6,
                "pressure_projected_at_response_kpa": 200.4,
                "temperature_control_due": True,
                "pressure_control_due": True,
            },
        )


def test_octos_chat_response_extracts_fenced_json_payload() -> None:
    result = parse_octos_chat_response(
        '{"text":"```json\\n{'
        '\\"temperature_c\\": 58.5, \\"confidence\\": 0.98'
        '}\\n```","model":"qwen3-vl:8b-instruct"}'
    )

    assert result == {"temperature_c": 58.5, "confidence": 0.98}


def test_octos_chat_response_rejects_runtime_error() -> None:
    with pytest.raises(ValueError, match="Octos failed"):
        parse_octos_chat_response('{"error":"provider timeout"}')
