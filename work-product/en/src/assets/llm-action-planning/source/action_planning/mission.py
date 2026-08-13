from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .plan_validator import validate_plan


def _resolve(reference: str, context: dict[str, Any]) -> Any:
    root, *parts = reference.split(".")
    if root not in context:
        raise KeyError(reference)
    value: Any = context[root]
    for part in parts:
        if not isinstance(value, dict) or part not in value:
            raise KeyError(reference)
        value = value[part]
    return value


def evaluate_condition(condition: dict[str, Any], context: dict[str, Any]) -> bool:
    if "all" in condition:
        return all(evaluate_condition(item, context) for item in condition["all"])
    if "any" in condition:
        return any(evaluate_condition(item, context) for item in condition["any"])
    actual = _resolve(condition["ref"], context)
    expected = condition["value"]
    return actual == expected if condition["op"] == "eq" else actual != expected


@dataclass(frozen=True)
class SkillRequest:
    step_id: str
    skill: str
    arguments: dict[str, Any]


class MissionMachine:
    def __init__(self, plan: dict[str, Any]):
        validate_plan(plan).require_valid()
        self.plan = plan
        self.index = 0
        self.pending: SkillRequest | None = None
        self.context: dict[str, Any] = {}
        self.events: list[dict[str, Any]] = []
        self.state = "READY"

    def _requested_switch_state(self) -> str | None:
        for step in reversed(self.plan["steps"][: self.index]):
            if step["skill"] != "set_switch_state":
                continue
            result = self.context.get(step["id"], {})
            if result.get("status") == "succeeded":
                return step["arguments"]["state"]
        return None

    def next_request(self) -> SkillRequest | None:
        if self.pending is not None:
            return self.pending
        if self.state in {"SUCCEEDED", "FAILED"}:
            return None
        steps = self.plan["steps"]
        while self.index < len(steps):
            step = steps[self.index]
            condition = step.get("when")
            if condition is not None and not evaluate_condition(condition, self.context):
                skipped = {"status": "skipped"}
                self.context[step["id"]] = skipped
                if "save_as" in step:
                    self.context[step["save_as"]] = skipped
                self.events.append(
                    {"event": "STEP_SKIPPED", "step_id": step["id"]}
                )
                self.index += 1
                continue
            self.pending = SkillRequest(
                step_id=step["id"],
                skill=step["skill"],
                arguments=step["arguments"],
            )
            self.state = "RUNNING"
            self.events.append(
                {
                    "event": "SKILL_REQUESTED",
                    "step_id": step["id"],
                    "skill": step["skill"],
                }
            )
            return self.pending
        self.state = "SUCCEEDED"
        self.events.append({"event": "MISSION_SUCCEEDED"})
        return None

    def accept_result(self, step_id: str, result: dict[str, Any]) -> None:
        if self.pending is None or self.pending.step_id != step_id:
            raise ValueError("result does not match the pending step")
        if result.get("status") not in {"succeeded", "failed"}:
            raise ValueError("skill result must have succeeded or failed status")
        result = dict(result)
        expected_state = self._requested_switch_state()
        if (
            self.pending.skill == "observe_switch"
            and result["status"] == "succeeded"
            and expected_state is not None
            and result.get("state") != expected_state
        ):
            result["status"] = "failed"
            result["detail"] = (
                f"visual verification expected {expected_state}, "
                f"observed {result.get('state', 'unknown')}"
            )
        step = self.plan["steps"][self.index]
        saved = result
        self.context[step["id"]] = saved
        if "save_as" in step:
            self.context[step["save_as"]] = saved
        self.events.append(
            {
                "event": "SKILL_COMPLETED",
                "step_id": step_id,
                "status": result["status"],
            }
        )
        self.pending = None
        self.index += 1
        if result["status"] == "failed":
            self.state = "FAILED"
            self.events.append(
                {"event": "MISSION_FAILED", "failed_step": step_id}
            )
