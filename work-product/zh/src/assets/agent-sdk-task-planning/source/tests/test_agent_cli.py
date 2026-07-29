import httpx
from pathlib import Path

from agent_cli import build_agent
from agent_tools import EventPrinter, RobotApiClient


def test_agent_is_built_with_atomic_robot_tools_and_bounded_turns():
    client = RobotApiClient(
        "http://robot.test",
        http_client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(500, json={})
            )
        ),
    )

    agent = build_agent(
        client,
        EventPrinter(),
        model_name="qwen3-vl:8b-instruct",
        ollama_url="http://127.0.0.1:11434/v1",
    )

    assert agent.name == "Dora robot operator"
    assert len(agent.tools) == 6
    assert "set_switch_state" not in {tool.name for tool in agent.tools}


def test_container_exports_the_agent_openai_base_url_variable():
    root = Path(__file__).resolve().parents[1]
    script = (root / "run-container.sh").read_text(encoding="utf-8")

    assert "OLLAMA_OPENAI_BASE_URL=" in script
