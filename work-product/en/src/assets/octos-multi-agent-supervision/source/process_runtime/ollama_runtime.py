from __future__ import annotations

import subprocess
import time
from collections.abc import Callable
from pathlib import Path


def unload_model(
    ollama: Path,
    model: str,
    *,
    settle_seconds: float = 2.0,
    runner: Callable = subprocess.run,
    sleeper: Callable[[float], None] = time.sleep,
) -> None:
    runner(
        [str(ollama), "stop", model],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=30,
    )
    sleeper(settle_seconds)
