#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


SAFE_BUILTINS = {
    "abs": abs,
    "len": len,
    "max": max,
    "min": min,
    "reversed": reversed,
    "round": round,
}


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("expected one policy path")
    source = Path(sys.argv[1]).read_text(encoding="utf-8")
    context = json.load(sys.stdin)
    namespace: dict = {}
    exec(
        compile(source, sys.argv[1], "exec"),
        {"__builtins__": SAFE_BUILTINS},
        namespace,
    )
    decision = namespace["decide"](context)
    json.dump(decision, sys.stdout, separators=(",", ":"))


if __name__ == "__main__":
    main()
