import json
import time

import pyarrow as pa
from dora import Node

from trajectory import TOTAL_FRAMES, frame_state


node = Node()

for frame in range(TOTAL_FRAMES):
    node.send_output("scene_state", pa.array([json.dumps(frame_state(frame))]))
    time.sleep(0.04)

time.sleep(1.0)
