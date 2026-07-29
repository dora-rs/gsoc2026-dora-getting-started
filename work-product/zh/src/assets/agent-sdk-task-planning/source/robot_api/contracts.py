from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


NamedLocation = Literal["home", "indicator_station", "main_switch"]
NamedArmPose = Literal["home", "ready", "press", "retract"]
ActionStatus = Literal[
    "accepted",
    "running",
    "succeeded",
    "failed",
    "rejected",
    "cancelled",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Pose2D(StrictModel):
    x: float
    y: float
    yaw: float


class RobotState(StrictModel):
    captured_at: datetime
    location: NamedLocation | Literal["unknown"]
    arm_pose: NamedArmPose | Literal["unknown"]
    navigation_active: bool
    arm_active: bool
    stopped: bool
    pose: Pose2D | None = None

    @model_validator(mode="after")
    def require_timezone(self):
        if self.captured_at.tzinfo is None:
            raise ValueError("captured_at must include a timezone")
        return self


class NavigateRequest(StrictModel):
    location: NamedLocation


class ObservationRequest(StrictModel):
    target: Literal["status_indicator"]


class ArmPoseRequest(StrictModel):
    pose: NamedArmPose


class StopRequest(StrictModel):
    reason: str = Field(min_length=1, max_length=160)


class ActionResponse(StrictModel):
    request_id: str = Field(min_length=1, max_length=96)
    action_id: str = Field(min_length=1, max_length=96)
    status: ActionStatus
    retryable: bool
    error_code: str | None = None
    message: str = Field(min_length=1, max_length=500)
    robot_state: RobotState
    result: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def require_failure_metadata(self):
        unsuccessful = {"failed", "rejected", "cancelled"}
        if self.status in unsuccessful and not self.error_code:
            raise ValueError(
                "failed, rejected, and cancelled responses require error_code"
            )
        if self.status not in unsuccessful and self.error_code:
            raise ValueError("successful responses cannot contain error_code")
        return self


def require_fresh_state(
    state: RobotState, *, max_age_seconds: float = 2.0
) -> RobotState:
    age = (datetime.now(timezone.utc) - state.captured_at).total_seconds()
    if age < -0.5:
        raise ValueError("robot state timestamp is in the future")
    if age > max_age_seconds:
        raise ValueError(
            f"robot state is stale ({age:.2f}s > {max_age_seconds:.2f}s)"
        )
    return state
