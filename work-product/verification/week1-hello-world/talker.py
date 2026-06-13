import pyarrow as pa
from dora import Node


node = Node()
count = 0

for event in node:
    if event["type"] == "INPUT":
        count += 1
        node.send_output("greeting", pa.array([f"Hello from dora-rs #{count}"]))
    elif event["type"] == "STOP":
        break
