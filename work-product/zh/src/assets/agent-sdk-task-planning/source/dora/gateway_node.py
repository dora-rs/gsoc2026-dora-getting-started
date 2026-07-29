#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

import uvicorn
from dora import Node


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common import read_json_event, send_json
from robot_api.contracts import RobotState
from robot_api.dora_broker import DoraBroker
from robot_api.gateway import create_app


def initial_state():
    return RobotState(
        captured_at=datetime(1970, 1, 1, tzinfo=timezone.utc),
        location="unknown",
        arm_pose="unknown",
        navigation_active=False,
        arm_active=False,
        stopped=False,
        pose=None,
    )


def main():
    broker = DoraBroker(initial_state())
    app = create_app(
        broker,
        max_state_age_seconds=float(
            os.getenv("WEEK10_STATE_MAX_AGE_S", "2.5")
        ),
    )
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host="127.0.0.1",
            port=int(os.getenv("WEEK10_API_PORT", "8000")),
            log_level="warning",
            access_log=False,
        )
    )
    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()
    dora = Node()
    outputs = {
        "navigate": "navigation_request",
        "arm": "arm_request",
        "observe": "observation_request",
        "stop": "stop_request",
    }
    try:
        for event in dora:
            if event["type"] == "STOP":
                break
            if event["type"] != "INPUT":
                continue
            if event["id"] == "tick":
                for dispatch in broker.drain():
                    send_json(
                        dora,
                        outputs[dispatch.kind],
                        {
                            "request_id": dispatch.request_id,
                            "action_id": dispatch.action_id,
                            **dispatch.payload,
                        },
                        "week10.action-request.v1",
                    )
            elif event["id"] == "state":
                broker.update_state(
                    RobotState.model_validate(read_json_event(event))
                )
            elif event["id"].endswith("_result"):
                broker.resolve(read_json_event(event))
    finally:
        server.should_exit = True
        server_thread.join(timeout=3)


if __name__ == "__main__":
    main()
