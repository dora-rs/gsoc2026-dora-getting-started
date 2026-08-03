from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_stop_uses_an_independent_dora_node():
    dataflow = (ROOT / "dora" / "dataflow.yml").read_text(
        encoding="utf-8"
    )

    assert "stop_result: stop/result" in dataflow
    assert "- id: stop\n    path: stop_node.py" in dataflow
    navigation = dataflow.split("- id: navigation", 1)[1].split(
        "- id: stop", 1
    )[0]
    assert "gateway/stop_request" not in navigation
