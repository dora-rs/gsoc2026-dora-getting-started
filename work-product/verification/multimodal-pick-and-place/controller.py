from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from contracts import ObservationResult


class State(Enum):
    WAITING = "waiting"
    INSPECTING_BEFORE = "inspecting_before"
    MOVING = "moving"
    INSPECTING_AFTER = "inspecting_after"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(frozen=True)
class Command:
    kind: str
    detail: str | None = None


class TaskController:
    def __init__(self, min_confidence: float = 0.8) -> None:
        self.min_confidence = min_confidence
        self.state = State.WAITING

    def start(self) -> list[Command]:
        if self.state is not State.WAITING:
            raise RuntimeError("task has already started")
        self.state = State.INSPECTING_BEFORE
        return [Command("capture", "before")]

    def on_analysis(
        self, phase: str, result: ObservationResult
    ) -> list[Command]:
        expected_state = {
            "before": State.INSPECTING_BEFORE,
            "after": State.INSPECTING_AFTER,
        }.get(phase)
        if expected_state is None or self.state is not expected_state:
            raise RuntimeError("analysis phase does not match controller state")

        visible = result.red_visible and result.blue_visible
        confident = result.confidence >= self.min_confidence

        if phase == "before":
            if visible and confident and not result.red_on_blue:
                self.state = State.MOVING
                return [Command("run_pick_place")]
            self.state = State.FAILED
            return [Command("task_failed", "precondition")]

        if visible and confident and result.red_on_blue:
            self.state = State.SUCCEEDED
            return [Command("task_success")]
        self.state = State.FAILED
        return [Command("task_failed", "postcondition")]

    def on_motion_complete(self, success: bool) -> list[Command]:
        if self.state is not State.MOVING:
            raise RuntimeError("motion result is not expected in current state")
        if not success:
            self.state = State.FAILED
            return [Command("task_failed", "motion")]
        self.state = State.INSPECTING_AFTER
        return [Command("capture", "after")]
