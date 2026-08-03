from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .contracts import PLAN_SCHEMA


STEP_ID = re.compile(r"^[a-z][a-z0-9_]{1,47}$")
FORBIDDEN_KEYS = {
    "x",
    "y",
    "z",
    "yaw",
    "velocity",
    "wheel_velocity",
    "joint",
    "joint_angle",
    "joint_angles",
    "motor",
    "command",
    "shell",
    "code",
}
ALLOWED_STEP_KEYS = {"id", "skill", "arguments", "save_as", "when"}
ALLOWED_SKILLS = {"navigate_to", "observe_switch", "set_switch_state"}


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    errors: tuple[str, ...]

    def require_valid(self) -> None:
        if not self.valid:
            raise ValueError("; ".join(self.errors))


def _forbidden_paths(value: Any, path: str = "$") -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in FORBIDDEN_KEYS:
                errors.append(f"{path}.{key} is forbidden")
            errors.extend(_forbidden_paths(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(_forbidden_paths(child, f"{path}[{index}]"))
    return errors


def _validate_arguments(skill: str, arguments: Any, path: str) -> list[str]:
    if not isinstance(arguments, dict):
        return [f"{path} must be an object"]
    if skill == "navigate_to":
        if set(arguments) != {"location"}:
            return [f"{path} must contain only location"]
        if arguments["location"] not in {"home", "main_switch"}:
            return [f"{path}.location must be a named location"]
    elif skill == "observe_switch":
        if arguments != {"switch_id": "main_switch"}:
            return [f"{path} must identify main_switch"]
    elif skill == "set_switch_state":
        if set(arguments) != {"switch_id", "state"}:
            return [f"{path} must contain switch_id and state"]
        if arguments["switch_id"] != "main_switch":
            return [f"{path}.switch_id must be main_switch"]
        if arguments["state"] not in {"on", "off"}:
            return [f"{path}.state must be on or off"]
    return []


def _validate_condition(
    condition: Any,
    available_roots: set[str],
    path: str,
) -> list[str]:
    if not isinstance(condition, dict):
        return [f"{path} must be an object"]
    if set(condition) in ({"all"}, {"any"}):
        key = next(iter(condition))
        values = condition[key]
        if not isinstance(values, list) or not values:
            return [f"{path}.{key} must be a non-empty array"]
        errors: list[str] = []
        for index, child in enumerate(values):
            errors.extend(
                _validate_condition(child, available_roots, f"{path}.{key}[{index}]")
            )
        return errors
    if set(condition) != {"ref", "op", "value"}:
        return [f"{path} must be a condition leaf or all/any group"]
    reference = condition["ref"]
    if not isinstance(reference, str) or "." not in reference:
        return [f"{path}.ref must use result.field notation"]
    root = reference.split(".", 1)[0]
    errors = []
    if root not in available_roots:
        errors.append(f"{path}.ref points to an unavailable result")
    if condition["op"] not in {"eq", "ne"}:
        errors.append(f"{path}.op must be eq or ne")
    if isinstance(condition["value"], (dict, list)):
        errors.append(f"{path}.value must be scalar")
    return errors


def validate_plan(plan: Any) -> ValidationResult:
    errors: list[str] = []
    if not isinstance(plan, dict):
        return ValidationResult(False, ("plan must be an object",))
    errors.extend(_forbidden_paths(plan))
    if set(plan) != {"schema", "goal", "steps"}:
        errors.append("plan must contain only schema, goal, and steps")
    if plan.get("schema") != PLAN_SCHEMA:
        errors.append("unsupported plan schema")
    goal = plan.get("goal")
    if not isinstance(goal, str) or not 1 <= len(goal) <= 160:
        errors.append("goal must be a non-empty string up to 160 characters")
    steps = plan.get("steps")
    if not isinstance(steps, list) or not 1 <= len(steps) <= 8:
        errors.append("steps must contain between 1 and 8 items")
        return ValidationResult(False, tuple(dict.fromkeys(errors)))

    seen_ids: set[str] = set()
    available_roots: set[str] = set()
    observation_seen = False
    for index, step in enumerate(steps):
        path = f"steps[{index}]"
        if not isinstance(step, dict):
            errors.append(f"{path} must be an object")
            continue
        extra = set(step) - ALLOWED_STEP_KEYS
        if extra:
            errors.append(f"{path} has unsupported fields: {sorted(extra)}")
        step_id = step.get("id")
        if not isinstance(step_id, str) or not STEP_ID.fullmatch(step_id):
            errors.append(f"{path}.id is invalid")
        elif step_id in seen_ids:
            errors.append(f"{path}.id is duplicated")
        else:
            seen_ids.add(step_id)
        skill = step.get("skill")
        if skill not in ALLOWED_SKILLS:
            errors.append(f"{path}.skill is not allowed")
        else:
            errors.extend(
                _validate_arguments(skill, step.get("arguments"), f"{path}.arguments")
            )
        if "when" in step:
            errors.extend(
                _validate_condition(step["when"], available_roots, f"{path}.when")
            )
        if skill == "set_switch_state":
            if "when" not in step:
                errors.append(f"{path} requires a condition")
            if not observation_seen:
                errors.append(f"{path} requires an earlier observation")
        if skill == "observe_switch":
            observation_seen = True
        save_as = step.get("save_as")
        if save_as is not None:
            if not isinstance(save_as, str) or not STEP_ID.fullmatch(save_as):
                errors.append(f"{path}.save_as is invalid")
            elif save_as in available_roots or save_as in seen_ids:
                errors.append(f"{path}.save_as is duplicated")
            else:
                available_roots.add(save_as)
        if isinstance(step_id, str) and STEP_ID.fullmatch(step_id):
            available_roots.add(step_id)

    final_step = steps[-1] if isinstance(steps[-1], dict) else {}
    if not (
        final_step.get("skill") == "navigate_to"
        and final_step.get("arguments") == {"location": "home"}
    ):
        errors.append("final step must navigate to home")
    return ValidationResult(not errors, tuple(dict.fromkeys(errors)))
