#!/usr/bin/env python3
import json
import sys
from pathlib import Path

import pyarrow as pa
from dora import Node


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from week9_validation.model_clients import request_action_plan


def main():
    manifest = json.loads(
        (ROOT / "config" / "skill_manifest.json").read_text(encoding="utf-8")
    )
    node = Node()
    planned = False
    for event in node:
        if event["type"] == "STOP":
            break
        if event["type"] != "INPUT" or planned:
            continue
        plan = request_action_plan("Turn off the main switch, then return home.", manifest)
        node.send_output(
            "plan",
            pa.array([json.dumps(plan, separators=(",", ":"))]),
            {"schema": plan["schema"]},
        )
        planned = True


if __name__ == "__main__":
    main()
