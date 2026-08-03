#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import threading
from pathlib import Path

import uvicorn
from dora import Node


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common import read_json_event, send_json
from week11_api.broker import DoraActionBroker
from week11_api.gateway import create_app


def initial_status() -> dict:
    return {
        "observer": {
            "location": "unknown",
            "docked": False,
            "navigation_active": False,
        },
        "operator": {
            "location": "unknown",
            "at_control": False,
            "navigation_active": False,
            "arm_active": False,
        },
        "process": {
            "cooling_on": False,
            "relief_open": False,
            "temperature_safe_min_c": 30.0,
            "temperature_safe_max_c": 60.0,
            "pressure_safe_min_kpa": 160.0,
            "pressure_safe_max_kpa": 200.0,
            "temperature_rate_c_per_s": 0.0,
            "pressure_rate_kpa_per_s": 0.0,
            "control_cycle_count": 0,
            "phase": "unknown",
        },
    }


def main() -> None:
    broker = DoraActionBroker(initial_status())
    server = uvicorn.Server(
        uvicorn.Config(
            create_app(broker),
            host="127.0.0.1",
            port=int(os.getenv("WEEK11_API_PORT", "8111")),
            log_level="warning",
            access_log=False,
        )
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    node = Node()
    output_for_kind = {
        "navigate": "command_request",
        "switch": "command_request",
        "observe": "observation_request",
        "activity": "activity_request",
    }
    try:
        for event in node:
            if event["type"] == "STOP":
                break
            if event["type"] != "INPUT":
                continue
            if event["id"] == "tick":
                for dispatch in broker.drain():
                    send_json(
                        node,
                        output_for_kind[dispatch.kind],
                        {
                            "request_id": dispatch.request_id,
                            "kind": dispatch.kind,
                            **dispatch.payload,
                        },
                        "week11.action-request.v1",
                    )
            elif event["id"] == "state":
                broker.update_status(read_json_event(event))
            elif event["id"].endswith("_result"):
                broker.resolve(read_json_event(event))
    finally:
        server.should_exit = True
        thread.join(timeout=3.0)


if __name__ == "__main__":
    main()
