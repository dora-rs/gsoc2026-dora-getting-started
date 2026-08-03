from pathlib import Path

from week11_runtime.ollama_runtime import unload_model


def test_unload_model_uses_the_selected_ollama_binary() -> None:
    calls = []
    sleeps = []

    def runner(command, **kwargs):
        calls.append((command, kwargs))

    unload_model(
        Path("/opt/ollama/bin/ollama"),
        "qwen3-vl:8b-instruct",
        settle_seconds=2.0,
        runner=runner,
        sleeper=sleeps.append,
    )

    assert calls[0][0] == [
        str(Path("/opt/ollama/bin/ollama")),
        "stop",
        "qwen3-vl:8b-instruct",
    ]
    assert calls[0][1]["check"] is True
    assert sleeps == [2.0]
