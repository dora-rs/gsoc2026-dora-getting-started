#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


SRC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SRC))

from week11_runtime.video_acceleration import accelerate_video  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--speed", type=float, default=2.5)
    args = parser.parse_args()

    output = accelerate_video(
        args.input,
        args.output,
        speed=args.speed,
    )
    print(
        json.dumps(
            {
                "input": str(args.input),
                "output": str(output),
                "speed": args.speed,
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
