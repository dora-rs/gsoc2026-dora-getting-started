#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from simulation_runtime import SimulationSession


PREFIX = "DORA_SIMULATION_RESULT "
root = Path(__file__).resolve().parent
output_dir = Path(
    os.environ.get("MULTIMODAL_OUTPUT", root / "outputs" / "dora-run")
)
trajectory_path = Path(
    os.environ.get(
        "MULTIMODAL_TRAJECTORY", root / "validated-trajectory.json"
    )
)


def emit(payload: dict[str, object]) -> None:
    print(PREFIX + json.dumps(payload, separators=(",", ":")), flush=True)


session = SimulationSession(output_dir, trajectory_path)
try:
    for line in sys.stdin:
        try:
            command = json.loads(line)
            kind = command["kind"]
            if kind == "capture":
                result = session.capture(command["phase"])
            elif kind == "run_pick_place":
                result = session.run_pick_place()
            elif kind == "finish":
                emit({"ok": True, "result": {"finished": True}})
                break
            else:
                raise ValueError(f"unknown simulation command: {kind}")
            emit({"ok": True, "result": result})
        except Exception as error:
            emit(
                {
                    "ok": False,
                    "error_type": type(error).__name__,
                    "message": str(error),
                }
            )
finally:
    session.close()
