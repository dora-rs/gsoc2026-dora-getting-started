#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from simulation_runtime import SimulationSession


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trajectory", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("outputs/demo"))
    args = parser.parse_args()

    session = SimulationSession(args.output, args.trajectory)
    try:
        before = session.capture("before")
        motion = session.run_pick_place()
        after = session.capture("after")
        result = {"before": before, "motion": motion, "after": after}
        (args.output / "run-result.json").write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(result, indent=2), flush=True)
        if not motion["success"]:
            raise SystemExit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()
