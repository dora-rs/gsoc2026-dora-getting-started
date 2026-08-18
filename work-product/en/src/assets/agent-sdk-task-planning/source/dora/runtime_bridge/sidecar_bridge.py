from __future__ import annotations

import json
import subprocess
from datetime import date, datetime, time


PREFIX = "DORA_SIDECAR_BRIDGE "


def json_default(value):
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode("utf-8")
    item = getattr(value, "item", None)
    if callable(item):
        return item()
    raise TypeError(
        f"Object of type {value.__class__.__name__} is not JSON serializable"
    )


class SidecarWorker:
    def __init__(self, command, *, cwd, env, log=print):
        self.log = log
        self.process_handle = subprocess.Popen(
            command,
            cwd=cwd,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

    def process(self, event):
        handle = self.process_handle
        if handle.stdin is None or handle.stdout is None:
            raise RuntimeError("sidecar pipes are unavailable")
        handle.stdin.write(
            json.dumps(event, separators=(",", ":"), default=json_default) + "\n"
        )
        handle.stdin.flush()
        outputs = []
        for line in handle.stdout:
            line = line.rstrip("\n")
            if not line.startswith(PREFIX):
                self.log(line)
                continue
            message = json.loads(line[len(PREFIX) :])
            if message["kind"] == "done":
                return outputs
            if message["kind"] == "output":
                outputs.append(message)
        raise RuntimeError(
            f"sidecar exited before completing event: {handle.returncode}"
        )

    def close(self):
        handle = self.process_handle
        if handle.poll() is None:
            if handle.stdin is not None:
                try:
                    handle.stdin.write('{"type":"STOP"}\n')
                    handle.stdin.flush()
                    handle.stdin.close()
                except BrokenPipeError:
                    pass
            try:
                handle.wait(timeout=5)
            except subprocess.TimeoutExpired:
                handle.terminate()
                handle.wait(timeout=5)
