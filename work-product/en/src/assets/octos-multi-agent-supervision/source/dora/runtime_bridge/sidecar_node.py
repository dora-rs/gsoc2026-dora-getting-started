#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path

import pyarrow as pa
from dora import Node

from sidecar_bridge import SidecarWorker


bridge_root = Path(__file__).resolve().parent
worker_script = Path(os.environ["DORA_WORKER_SCRIPT"])
worker_cwd = Path(os.environ.get("DORA_WORKER_CWD", worker_script.parent))
worker_python = os.environ.get("DORA_WORKER_PYTHON", "/usr/bin/python3")
worker_env = os.environ.copy()
worker_env["PYTHONPATH"] = os.pathsep.join(
    [
        str(bridge_root / "worker_shim"),
        worker_env.get("DORA_WORKER_PYTHONPATH", ""),
    ]
).rstrip(os.pathsep)

node = Node()
worker = SidecarWorker(
    [worker_python, "-u", str(worker_script)],
    cwd=worker_cwd,
    env=worker_env,
    log=lambda line: print(f"SIDECAR {worker_script.name}: {line}", flush=True),
)
try:
    for event in node:
        if event["type"] == "STOP":
            break
        if event["type"] != "INPUT":
            continue
        request = {
            "type": "INPUT",
            "id": event["id"],
            "value": event["value"].to_pylist(),
            "metadata": event.get("metadata", {}),
        }
        for output in worker.process(request):
            node.send_output(
                output["id"],
                pa.array(output["value"]),
                output.get("metadata", {}),
            )
finally:
    worker.close()
