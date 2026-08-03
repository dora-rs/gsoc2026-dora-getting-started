from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_dataflow_routes_commands_and_observations_through_dora() -> None:
    dataflow = yaml.safe_load(
        (ROOT / "dora" / "week11_dataflow.yml").read_text(
            encoding="utf-8"
        )
    )
    nodes = {node["id"]: node for node in dataflow["nodes"]}

    assert set(nodes) == {
        "gateway",
        "state",
        "command",
        "observation",
        "activity",
    }
    assert nodes["command"]["inputs"]["action"] == "gateway/command_request"
    assert (
        nodes["observation"]["inputs"]["observe"]
        == "gateway/observation_request"
    )
    assert (
        nodes["activity"]["inputs"]["activity"]
        == "gateway/activity_request"
    )
    assert nodes["gateway"]["inputs"]["state"] == "state/state"


def test_container_uses_adaptive_process_defaults() -> None:
    script = (ROOT / "run-container.sh").read_text(encoding="utf-8")

    for expected in (
        'WEEK11_IMAGE:-octos-process-supervision:humble',
        'WEEK11_CONTAINER:-octos-process-supervision',
        'WEEK11_WORKSPACE:-${PWD}',
        'WEEK11_INITIAL_TEMPERATURE_C:-32.0',
        'WEEK11_INITIAL_PRESSURE_KPA:-162.0',
        'WEEK11_HEATING_RATE_C_PER_S:-0.25',
        'WEEK11_PRESSURE_RATE_KPA_PER_S:-0.32',
        'WEEK11_COOLING_EFFECT_C_PER_S:--1.35',
        'WEEK11_RELIEF_EFFECT_KPA_PER_S:--3.50',
    ):
        assert expected in script
