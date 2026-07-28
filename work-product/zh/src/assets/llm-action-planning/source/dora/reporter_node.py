#!/usr/bin/env python3
import json
import os
import time
from pathlib import Path

from dora import Node


OUTPUT = Path(os.getenv("WEEK9_OUTPUT_DIR", "/workspace/outputs")) / "mission-events.jsonl"


def main():
    node = Node()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("a", encoding="utf-8") as stream:
        for event in node:
            if event["type"] == "STOP":
                break
            if event["type"] != "INPUT" or event["id"] != "status":
                continue
            payload = json.loads(event["value"].to_pylist()[0])
            payload.setdefault("reported_at_unix_s", round(time.time(), 6))
            stream.write(json.dumps(payload, separators=(",", ":")) + "\n")
            stream.flush()
            print(json.dumps(payload, indent=2), flush=True)


if __name__ == "__main__":
    main()
