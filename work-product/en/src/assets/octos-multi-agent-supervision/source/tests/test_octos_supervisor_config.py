import json
from pathlib import Path


def test_supervisor_profile_exposes_no_tools() -> None:
    config_path = (
        Path(__file__).resolve().parents[1]
        / "config"
        / "octos-supervisor.json"
    )
    config = json.loads(config_path.read_text(encoding="utf-8"))

    assert config["tool_policy"]["allow"] == ["__no_tools__"]
