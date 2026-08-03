from __future__ import annotations

import json
import sys
from typing import Literal, TextIO

import httpx
from agents import function_tool


AGENT_INSTRUCTIONS = """
You operate a simulated mobile manipulator through safe named tools.

Rules:
- Read fresh robot state before deciding what to do.
- Navigate to indicator_station and observe status_indicator first.
- If the indicator is visible and lit, navigate to main_switch and use this
  exact arm sequence:
  ready -> press -> retract -> home.
- If the indicator is unlit, do not press the switch.
- After a press, return to indicator_station and observe status_indicator
  again. Retry observation once when the result is unknown or low confidence;
  never blindly repeat press.
- Return the arm home before navigation.
- Navigate home and verify that the final robot location is home and the arm
  pose is home.
- Stop and report the structured error when an action is rejected or a
  non-retryable failure occurs.
- Never invent coordinates, velocities, motor commands, joint angles, shell
  commands, or tools that are not available.
- Keep the final answer concise and describe only observable tool results.
""".strip()

_DEFAULT_STREAM = object()

class EventPrinter:
    def __init__(self, stream: TextIO | None | object = _DEFAULT_STREAM):
        self.stream = sys.stdout if stream is _DEFAULT_STREAM else stream

    def emit(self, event: str, message: str, **fields) -> None:
        if self.stream is None:
            return
        suffix = " ".join(
            f"{key}={json.dumps(value, ensure_ascii=False)}"
            for key, value in fields.items()
        )
        line = f"[{event}] {message}"
        if suffix:
            line += f" {suffix}"
        print(line, file=self.stream, flush=True)


class RobotApiClient:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        *,
        timeout_seconds: float = 210.0,
        http_client: httpx.Client | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.http = http_client or httpx.Client(timeout=timeout_seconds)

    def _request(self, method: str, path: str, **kwargs) -> dict:
        response = self.http.request(
            method, f"{self.base_url}{path}", **kwargs
        )
        payload = response.json()
        if response.is_error and not isinstance(payload, dict):
            response.raise_for_status()
        return payload

    def get_robot_state(self) -> dict:
        return self._request("GET", "/v1/robot/state")

    def navigate(
        self, location: Literal["home", "indicator_station", "main_switch"]
    ) -> dict:
        return self._request(
            "POST",
            "/v1/actions/navigate",
            json={"location": location},
        )

    def observe(self, target: Literal["status_indicator"]) -> dict:
        return self._request(
            "POST",
            "/v1/actions/observe",
            json={"target": target},
        )

    def move_arm(
        self, pose: Literal["home", "ready", "press", "retract"]
    ) -> dict:
        return self._request(
            "POST",
            "/v1/actions/arm",
            json={"pose": pose},
        )

    def get_action_status(self, action_id: str) -> dict:
        return self._request("GET", f"/v1/actions/{action_id}")

    def stop(self, reason: str) -> dict:
        return self._request(
            "POST",
            "/v1/stop",
            json={"reason": reason},
        )


def build_tools(client: RobotApiClient, events: EventPrinter):
    def render(payload: dict) -> str:
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    @function_tool
    def get_robot_state() -> str:
        """Read the latest authoritative robot motion state."""
        payload = client.get_robot_state()
        events.emit(
            "STATE",
            "robot state",
            location=payload.get("location"),
            arm_pose=payload.get("arm_pose"),
        )
        return render(payload)

    @function_tool
    def navigate_to_named_pose(
        location: Literal["home", "indicator_station", "main_switch"],
    ) -> str:
        """Navigate through a validated route to a named location."""
        events.emit("TOOL", "navigate_to_named_pose", location=location)
        payload = client.navigate(location)
        events.emit("RESULT", "navigation", status=payload.get("status"))
        return render(payload)

    @function_tool
    def capture_observation(
        target: Literal["status_indicator"],
    ) -> str:
        """Capture RGB data and classify the named indicator state."""
        events.emit("TOOL", "capture_observation", target=target)
        payload = client.observe(target)
        events.emit(
            "RESULT",
            "observation",
            status=payload.get("status"),
            observation=payload.get("result"),
        )
        return render(payload)

    @function_tool
    def move_arm_to_named_pose(
        pose: Literal["home", "ready", "press", "retract"],
    ) -> str:
        """Move the arm to one validated, bounded, named pose."""
        events.emit("TOOL", "move_arm_to_named_pose", pose=pose)
        payload = client.move_arm(pose)
        events.emit("RESULT", "arm", status=payload.get("status"), pose=pose)
        return render(payload)

    @function_tool
    def get_action_status(action_id: str) -> str:
        """Read the stored result for an action identifier."""
        events.emit("TOOL", "get_action_status", action_id=action_id)
        return render(client.get_action_status(action_id))

    @function_tool
    def stop_robot(reason: str) -> str:
        """Stop active robot actions and move the arm toward home."""
        events.emit("TOOL", "stop_robot", reason=reason)
        payload = client.stop(reason)
        events.emit("RESULT", "stop", status=payload.get("status"))
        return render(payload)

    return [
        get_robot_state,
        navigate_to_named_pose,
        capture_observation,
        move_arm_to_named_pose,
        get_action_status,
        stop_robot,
    ]
