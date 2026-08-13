from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any


PREFIX = "DORA_BRIDGE_RESULT "


class JsonLineWorker:
    def __init__(
        self,
        command: Sequence[str],
        *,
        cwd: Path,
        env: Mapping[str, str],
        log: Callable[[str], None],
    ) -> None:
        self._log = log
        self._process = subprocess.Popen(
            list(command),
            cwd=cwd,
            env=dict(env),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

    def request(self, payload: dict[str, Any]) -> dict[str, Any]:
        stdin = self._process.stdin
        stdout = self._process.stdout
        if stdin is None or stdout is None:
            raise RuntimeError("worker pipes are unavailable")
        stdin.write(json.dumps(payload, separators=(",", ":")) + "\n")
        stdin.flush()
        while True:
            line = stdout.readline()
            if not line:
                raise RuntimeError(
                    f"worker exited before replying (code={self._process.poll()})"
                )
            if not line.startswith(PREFIX):
                self._log(line.rstrip())
                continue
            response = json.loads(line[len(PREFIX) :])
            if not response.get("ok"):
                raise RuntimeError(
                    f"worker failed: {response.get('error_type', 'unknown')}"
                )
            return response["result"]

    def close(self) -> None:
        if self._process.poll() is not None:
            return
        if self._process.stdin is not None:
            self._process.stdin.close()
        try:
            self._process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self._process.terminate()
            self._process.wait(timeout=5)
