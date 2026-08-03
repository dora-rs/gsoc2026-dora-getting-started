from __future__ import annotations

import json
from dataclasses import dataclass


VALID_SWITCHES = {"cooling", "relief"}


@dataclass(frozen=True)
class StrategyProposal:
    source: str
    reason: str


@dataclass(frozen=True)
class SwitchAction:
    switch: str
    enabled: bool


@dataclass(frozen=True)
class ScheduledSwitchAction:
    switch: str
    enabled: bool
    after_seconds: int


@dataclass(frozen=True)
class SupervisorDecision:
    actions_now: tuple[SwitchAction, ...]
    scheduled_actions: tuple[ScheduledSwitchAction, ...]
    next_observation_seconds: int
    done: bool
    reason: str


def completion_contract_ready(
    observation: dict,
    switch_state: dict[str, bool],
    *,
    round_number: int,
    post_action_observation: bool,
) -> bool:
    return (
        round_number >= 2
        and post_action_observation
        and not switch_state["cooling"]
        and not switch_state["relief"]
        and float(observation["temperature_c"]) <= 60.0
        and float(observation["pressure_kpa"]) <= 200.0
    )


def validate_predictive_decision(
    decision: SupervisorDecision,
    switch_state: dict[str, bool],
    observation: dict,
    *,
    round_number: int,
    post_action_observation: bool,
    metrics: dict | None = None,
) -> None:
    completion_ready = completion_contract_ready(
        observation,
        switch_state,
        round_number=round_number,
        post_action_observation=post_action_observation,
    )
    if decision.done:
        if not completion_ready:
            raise ValueError("done is true before completion conditions are met")
        if decision.actions_now or decision.scheduled_actions:
            raise ValueError("done cannot include control actions")
        return
    if completion_ready:
        raise ValueError("safe post-action observation requires done=true")

    immediate_seen: set[str] = set()
    active = dict(switch_state)
    newly_enabled: set[str] = set()

    for action in decision.actions_now:
        if action.switch in immediate_seen:
            raise ValueError(
                f"{action.switch} appears more than once in actions_now"
            )
        immediate_seen.add(action.switch)
        if active[action.switch] is action.enabled:
            state = str(action.enabled).lower()
            raise ValueError(f"{action.switch} is already {state}")
        active[action.switch] = action.enabled
        if action.enabled:
            newly_enabled.add(action.switch)

    scheduled_seen: set[str] = set()
    for action in decision.scheduled_actions:
        if action.switch in scheduled_seen:
            raise ValueError(
                f"{action.switch} appears more than once in scheduled_actions"
            )
        scheduled_seen.add(action.switch)
        if action.enabled:
            raise ValueError("scheduled actions must disable a switch")
        if not active[action.switch]:
            raise ValueError(
                f"{action.switch} is not active and cannot be scheduled off"
            )

    missing_shutdown = newly_enabled - scheduled_seen
    if missing_shutdown:
        switches = ", ".join(sorted(missing_shutdown))
        raise ValueError(
            f"newly enabled switch requires scheduled shutdown: {switches}"
        )

    if metrics is not None:
        control_due = {
            "cooling": bool(
                metrics.get(
                    "temperature_control_due",
                    float(
                        metrics.get(
                            "temperature_projected_if_wait_c",
                            metrics["temperature_projected_at_response_c"],
                        )
                    )
                    >= 58.0,
                )
            ),
            "relief": bool(
                metrics.get(
                    "pressure_control_due",
                    float(
                        metrics.get(
                            "pressure_projected_if_wait_kpa",
                            metrics["pressure_projected_at_response_kpa"],
                        )
                    )
                    >= 195.0,
                )
            ),
        }
        action_map = {
            action.switch: action.enabled
            for action in decision.actions_now
        }
        for switch in VALID_SWITCHES:
            enable_now = action_map.get(switch) is True
            if (
                not switch_state[switch]
                and control_due[switch]
                and not enable_now
            ):
                raise ValueError(
                    f"{switch} must be enabled before its projected boundary"
                )
            if enable_now and not control_due[switch]:
                raise ValueError(
                    f"{switch} action is too early for the response window"
                )

        shutdown_by_switch = {
            action.switch: action.after_seconds
            for action in decision.scheduled_actions
        }
        shutdown_metrics = {
            "cooling": (
                "temperature_projected_at_response_c",
                "cooling_net_rate_c_per_s",
                55.0,
                58.0,
            ),
            "relief": (
                "pressure_projected_at_response_kpa",
                "relief_net_rate_kpa_per_s",
                185.0,
                195.0,
            ),
        }
        active_overhead = float(
            metrics.get("switch_active_overhead_seconds", 3.0)
        )
        dual_switch_minimum = 6.0 if len(newly_enabled) == 2 else 0.0
        for switch in newly_enabled:
            projected_field, rate_field, lower, upper = shutdown_metrics[
                switch
            ]
            if rate_field not in metrics:
                continue
            active_seconds = max(
                float(shutdown_by_switch[switch]) + active_overhead,
                dual_switch_minimum,
            )
            projected_at_shutdown = float(metrics[projected_field]) + (
                float(metrics[rate_field]) * active_seconds
            )
            if projected_at_shutdown > upper:
                raise ValueError(
                    f"{switch} shutdown remains above operating band"
                )
            if projected_at_shutdown < lower:
                raise ValueError(
                    f"{switch} shutdown falls below operating band"
                )

def ensure_actions_change_state(
    decision: SupervisorDecision, switch_state: dict[str, bool]
) -> None:
    active = dict(switch_state)
    for action in decision.actions_now:
        if active[action.switch] is action.enabled:
            state = str(action.enabled).lower()
            raise ValueError(f"{action.switch} is already {state}")
        active[action.switch] = action.enabled


def ensure_decision_follows_hysteresis(
    decision: SupervisorDecision,
    observation: dict,
    switch_state: dict[str, bool],
    *,
    round_number: int,
    post_action_observation: bool,
) -> None:
    validate_predictive_decision(
        decision,
        switch_state,
        observation,
        round_number=round_number,
        post_action_observation=post_action_observation,
    )


def required_hysteresis_actions(
    _observation: dict,
    _switch_state: dict[str, bool],
) -> tuple[SwitchAction, ...]:
    return ()


def _extract_json(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        first_newline = stripped.find("\n")
        last_fence = stripped.rfind("```")
        if first_newline == -1 or last_fence <= first_newline:
            raise ValueError("invalid fenced JSON")
        stripped = stripped[first_newline + 1 : last_fence].strip()
    return stripped


def extract_octos_text(stdout: str) -> str:
    try:
        response = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise ValueError("Octos response is not valid JSON") from exc

    if not isinstance(response, dict):
        raise ValueError("Octos response must be a JSON object")
    if response.get("error"):
        raise ValueError(f"Octos failed: {response['error']}")

    text = response.get("text")
    if not isinstance(text, str):
        raise ValueError("Octos response does not contain text")
    return text


def parse_octos_chat_response(stdout: str) -> dict:
    text = extract_octos_text(stdout)
    try:
        payload = json.loads(_extract_json(text))
    except json.JSONDecodeError as exc:
        raise ValueError("Octos text does not contain valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("Octos text payload must be a JSON object")
    return payload


def parse_strategy_proposal(text: str) -> StrategyProposal:
    try:
        payload = json.loads(_extract_json(text))
    except json.JSONDecodeError as exc:
        raise ValueError("strategy proposal is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("strategy proposal must be a JSON object")
    source = payload.get("strategy_source")
    if not isinstance(source, str) or not source.strip():
        raise ValueError("strategy_source must be a non-empty string")
    reason = payload.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("strategy reason must be a non-empty string")
    return StrategyProposal(source=source, reason=reason.strip())


def _parse_switch_action(raw_action: object) -> SwitchAction:
    if not isinstance(raw_action, dict):
        raise ValueError("each switch action must be an object")
    switch = raw_action.get("switch")
    enabled = raw_action.get("enabled")
    if switch not in VALID_SWITCHES:
        raise ValueError("switch must be cooling or relief")
    if not isinstance(enabled, bool):
        raise ValueError("switch enabled must be a boolean")
    return SwitchAction(switch=switch, enabled=enabled)


def _parse_scheduled_action(raw_action: object) -> ScheduledSwitchAction:
    action = _parse_switch_action(raw_action)
    assert isinstance(raw_action, dict)
    after_seconds = raw_action.get("after_seconds")
    if (
        not isinstance(after_seconds, int)
        or isinstance(after_seconds, bool)
        or not 2 <= after_seconds <= 30
    ):
        raise ValueError(
            "scheduled action after_seconds must be between 2 and 30"
        )
    return ScheduledSwitchAction(
        switch=action.switch,
        enabled=action.enabled,
        after_seconds=after_seconds,
    )


def parse_supervisor_decision(text: str) -> SupervisorDecision:
    try:
        data = json.loads(_extract_json(text))
    except json.JSONDecodeError as exc:
        raise ValueError("supervisor response is not valid JSON") from exc

    if not isinstance(data, dict):
        raise ValueError("supervisor response must be a JSON object")

    raw_actions = data.get("actions_now")
    if not isinstance(raw_actions, list):
        raise ValueError("actions_now must be a list")
    actions = tuple(_parse_switch_action(item) for item in raw_actions)

    raw_scheduled = data.get("scheduled_actions")
    if not isinstance(raw_scheduled, list):
        raise ValueError("scheduled_actions must be a list")
    scheduled = tuple(
        _parse_scheduled_action(item) for item in raw_scheduled
    )

    interval = data.get("next_observation_seconds")
    if (
        not isinstance(interval, int)
        or isinstance(interval, bool)
        or not 2 <= interval <= 12
    ):
        raise ValueError(
            "next observation interval must be between 2 and 12 seconds"
        )

    done = data.get("done")
    if not isinstance(done, bool):
        raise ValueError("done must be a boolean")

    reason = data.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("reason must be a non-empty string")

    return SupervisorDecision(
        actions_now=actions,
        scheduled_actions=scheduled,
        next_observation_seconds=interval,
        done=done,
        reason=reason.strip(),
    )
