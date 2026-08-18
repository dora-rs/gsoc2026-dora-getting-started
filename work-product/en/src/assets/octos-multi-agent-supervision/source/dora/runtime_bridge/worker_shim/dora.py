from __future__ import annotations

import json
import sys

import pyarrow as pa


PREFIX = "DORA_SIDECAR_BRIDGE "


def _emit(payload):
    print(PREFIX + json.dumps(payload, separators=(",", ":")), flush=True)


class Node:
    def __iter__(self):
        for line in sys.stdin:
            request = json.loads(line)
            if request.get("type") == "STOP":
                yield {"type": "STOP"}
                return
            yield {
                "type": request["type"],
                "id": request.get("id"),
                "value": pa.array(request.get("value", [])),
                "metadata": request.get("metadata", {}),
            }
            _emit({"kind": "done"})

    def send_output(self, output_id, value, metadata=None):
        _emit(
            {
                "kind": "output",
                "id": output_id,
                "value": value.to_pylist(),
                "metadata": metadata or {},
            }
        )
