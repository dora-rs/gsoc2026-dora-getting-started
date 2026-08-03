import json
from datetime import datetime, timezone

import httpx

from agent_tools import (
    AGENT_INSTRUCTIONS,
    EventPrinter,
    RobotApiClient,
    build_tools,
)


def robot_state():
    return {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "location": "home",
        "arm_pose": "home",
        "navigation_active": False,
        "arm_active": False,
        "stopped": False,
        "pose": {"x": -2.8, "y": -1.8, "yaw": 0.0},
    }


def response(request):
    if request.url.path == "/v1/robot/state":
        return httpx.Response(200, json=robot_state())
    return httpx.Response(
        200,
        json={
            "request_id": "req-1",
            "action_id": "act-1",
            "status": "succeeded",
            "retryable": False,
            "error_code": None,
            "message": "ok",
            "robot_state": robot_state(),
            "result": {},
        },
    )


def test_robot_api_client_uses_only_named_action_payloads():
    transport = httpx.MockTransport(response)
    client = RobotApiClient(
        "http://robot.test",
        http_client=httpx.Client(transport=transport),
    )

    assert client.get_robot_state()["location"] == "home"
    assert client.navigate("main_switch")["status"] == "succeeded"
    assert client.move_arm("ready")["status"] == "succeeded"


def test_agents_sdk_exposes_only_safe_atomic_tools():
    tools = build_tools(
        RobotApiClient(
            "http://robot.test",
            http_client=httpx.Client(transport=httpx.MockTransport(response)),
        ),
        EventPrinter(stream=None),
    )
    names = {tool.name for tool in tools}

    assert names == {
        "get_robot_state",
        "navigate_to_named_pose",
        "capture_observation",
        "move_arm_to_named_pose",
        "get_action_status",
        "stop_robot",
    }
    schemas = json.dumps(
        {tool.name: tool.params_json_schema for tool in tools}
    )
    assert "linear_velocity" not in schemas
    assert "joint_angles" not in schemas
    assert "coordinates" not in schemas


def test_agent_policy_requires_observation_and_final_home_verification():
    assert "indicator_station" in AGENT_INSTRUCTIONS
    assert "status_indicator" in AGENT_INSTRUCTIONS
    assert "ready -> press -> retract -> home" in AGENT_INSTRUCTIONS
    assert "do not press" in AGENT_INSTRUCTIONS.lower()
    assert "verify" in AGENT_INSTRUCTIONS.lower()
    assert "location is home" in AGENT_INSTRUCTIONS.lower()


def test_event_printer_outputs_events_without_hidden_reasoning(capsys):
    printer = EventPrinter()
    printer.emit("TOOL", "navigate_to_named_pose", location="main_switch")

    output = capsys.readouterr().out
    assert output.startswith("[TOOL]")
    assert "main_switch" in output
    assert "reasoning" not in output.lower()
