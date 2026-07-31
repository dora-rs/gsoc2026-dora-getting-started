import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "octos-skills" / "week11-process-supervision"


def test_octos_skill_exposes_named_process_and_independent_action_tools() -> None:
    manifest = json.loads(
        (SKILL / "manifest.json").read_text(encoding="utf-8")
    )
    tool_names = {tool["name"] for tool in manifest["tools"]}

    assert tool_names == {
        "get_status",
        "navigate_robot",
        "read_pressure",
        "read_temperature",
        "apply_switch_actions",
        "report_activity",
        "wait_seconds",
    }
    serialized = json.dumps(
        [
            tool["input_schema"].get("properties", {})
            for tool in manifest["tools"]
        ]
    )
    for forbidden in ("joint_angle", "wheel_speed", "coordinate"):
        assert forbidden not in serialized

    switch_actions = next(
        tool
        for tool in manifest["tools"]
        if tool["name"] == "apply_switch_actions"
    )
    actions = switch_actions["input_schema"]["properties"]["actions"]
    action_id = switch_actions["input_schema"]["properties"]["action_id"]
    assert action_id["type"] == "string"
    assert set(switch_actions["input_schema"]["required"]) == {
        "action_id",
        "actions",
    }
    assert actions["minItems"] == 1
    assert actions["maxItems"] == 2
    assert "disable_after_seconds" not in (
        actions["items"]["properties"]
    )
    wait_tool = next(
        tool for tool in manifest["tools"] if tool["name"] == "wait_seconds"
    )
    seconds = wait_tool["input_schema"]["properties"]["seconds"]
    assert seconds["minimum"] == 1
    assert seconds["maximum"] == 120
    entrypoint = (SKILL / "main").read_text(encoding="utf-8")
    assert 'tool_name == "apply_switch_actions"' in entrypoint
    assert "execute_switch_actions_once(" in entrypoint
    assert "SOURCE_ROOT = Path.cwd()" in entrypoint
    assert 'nested_source = SOURCE_ROOT / "src"' in entrypoint
    assert "sleep=time.sleep" not in entrypoint
    assert "monotonic=time.monotonic" not in entrypoint


def test_skill_instructions_define_three_agent_roles() -> None:
    instructions = (SKILL / "SKILL.md").read_text(encoding="utf-8")

    assert "Supervisor" in instructions
    assert "Observer" in instructions
    assert "Operator" in instructions
    assert "30-60 C" in instructions
    assert "160-200 kPa" in instructions
    assert "process starts immediately" in instructions
    assert "choose when to observe" in instructions
    assert "apply_switch_actions" in instructions
    for fixed_policy in (
        "2 to 12 seconds",
        "Observer before Operator",
        "55-58 C",
        "185-195 kPa",
        "execute_control_plan",
    ):
        assert fixed_policy not in instructions


def test_switch_action_tool_reads_nested_process_status() -> None:
    entrypoint = (SKILL / "main").read_text(encoding="utf-8")

    assert 'status.get("process"' in entrypoint
