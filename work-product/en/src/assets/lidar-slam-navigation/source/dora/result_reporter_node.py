#!/usr/bin/env python3
import json

from dora import Node


def main():
    node = Node()
    previous_state = None
    for event in node:
        if event["type"] == "STOP":
            break
        if event["type"] != "INPUT" or event["id"] != "mission":
            continue
        payload = json.loads(event["value"].to_pylist()[0])
        state = payload["state"]
        if state != previous_state:
            print(
                f"DORA_MISSION state={state} detail={payload['detail']}",
                flush=True,
            )
            previous_state = state


if __name__ == "__main__":
    main()
