# Dora-Controlled Motion in a Rerun Scene

## Version Information

This chapter was verified on the same Linux desktop environment as the static
Rerun scene.

- Operating system: Ubuntu 22.04.5 LTS, x86_64
- Python: CPython 3.10.12
- Dora CLI: 0.5.0
- dora-rs Python package: `dora-rs==0.5.0`
- Rerun CLI and Python SDK: 0.33.0
- uv: 0.11.17
- pyarrow: 24.0.0
- PyYAML: 6.0.3
- Verification example: `verification/week2-rerun-scene`

## Goal

The previous chapter built a static Rerun scene. This chapter keeps the same
floor, cube, cylinder, robot, and car, then uses Dora to drive motion:

- Dora runs a `controller` node and a `visualizer` node.
- The controller publishes a sequence of scene states.
- The robot starts first, goes around the cube, approaches the cylinder, and
  stops.
- The car starts later, follows its own path around the cube, approaches the
  cylinder, and stops.
- Rerun records the changing transforms and captures a short Viewer recording.

<video controls muted loop src="../assets/week2-rerun-scene/rerun_viewer_recording.mp4"></video>

## Ask Codex to Add Dora Motion

Start from the static scene directory created in the previous chapter. Then ask
Codex CLI to extend it:

```text
I already have a static Rerun scene with a floor, cube obstacle, cylinder goal,
humanoid robot glTF model, and small car glTF model.

Please search the latest official Dora and Rerun documentation before choosing
commands or APIs. Keep the existing static scene structure and add Dora-driven
motion.

Target:
- Use dora-rs and dora-rs-cli.
- Create a Dora dataflow with a controller node and a visualizer node.
- The controller should publish scene state as JSON through Apache Arrow.
- The visualizer should receive scene state and update Rerun Transform3D values.
- The robot should start first, go around the cube, approach the cylinder, and
  stop.
- The car should start later, go around the cube on a separate lane, approach
  the cylinder, and stop.
- The Rerun Viewer recording should show the scene from the starting positions,
  not only the final state.

Please update the run script so it:
1. Creates or reuses the virtual environment.
2. Installs pinned Dora and Rerun dependencies.
3. Prints OS, Python, Dora, Rerun, and key package versions.
4. Runs the Dora dataflow.
5. Saves a .rrd recording.
6. Opens the Rerun Viewer and records only the Viewer window when a desktop
   display is available.
7. Fails if the .rrd recording was not created.

After running it, document any pitfalls and update the tutorial notes.
```

This prompt tells the assistant to preserve the static scene and add only the
motion layer. It also asks for one important recording detail: capture the Rerun
Viewer window itself, and give the recording enough time to show the actors at
their starting positions before they move.

## Dora Dataflow

The dataflow has two nodes:

```yaml
nodes:
  - id: controller
    path: controller.py
    outputs:
      - scene_state

  - id: visualizer
    path: visualizer.py
    inputs:
      scene_state: controller/scene_state
```

The controller owns the motion state. The visualizer owns the Rerun recording.
That boundary keeps the example close to a real robotics system: one part
publishes state, another part observes and renders it.

## Trajectory

The path is defined once in `trajectory.py`. Dora publishes sampled states, and
Rerun records the resulting model transforms.

```python
TOTAL_FRAMES = 260

ROBOT_PATH = [
    (-4.0, -0.85),
    (-1.6, -0.85),
    (-0.8, -1.65),
    (0.8, -1.65),
    (1.55, -0.85),
    (3.25, -0.35),
    (3.85, -0.25),
]

CAR_PATH = [
    (-4.4, 0.85),
    (-1.7, 0.85),
    (-0.85, 1.65),
    (0.85, 1.65),
    (1.65, 0.85),
    (3.35, 0.35),
    (4.15, 0.25),
]
```

The first part of the timeline intentionally holds both actors at their start
positions. This gives the Viewer recording time to start before the motion
begins. The robot starts first; the car starts later, so the two actors move in
sequence instead of arriving at the obstacle together.

## Controller Node

`controller.py` sends JSON scene state through Dora as an Apache Arrow string.
For a first Dora and Rerun example, JSON is easy to inspect and debug.

```python
import json
import time

import pyarrow as pa
from dora import Node

from trajectory import TOTAL_FRAMES, frame_state

node = Node()

for frame in range(TOTAL_FRAMES):
    node.send_output("scene_state", pa.array([json.dumps(frame_state(frame))]))
    time.sleep(0.04)
```

In a larger project, you may replace this JSON payload with a more structured
Arrow schema. The tutorial starts with the smallest shape that makes the data
flow visible.

## Visualizer Node

`visualizer.py` receives scene state, logs the static scene once, and logs the
moving actors at each frame.

```python
import json

import rerun as rr
from dora import Node

node = Node()

for event in node:
    if event["type"] == "INPUT" and event["id"] == "scene_state":
        state = json.loads(event["value"][0].as_py())
        rr.set_time("frame", sequence=state["frame"])
        robot = state["objects"]["robot"]
        rr.log(
            "world/actors/robot",
            rr.Transform3D(translation=[robot["x"], robot["y"], 0.0]),
        )
    elif event["type"] == "STOP":
        break
```

The actual file updates both robot and car transforms, including heading, while
the cube, cylinder, floor, and glTF assets remain static.

## Run the Dora-Controlled Scene

Run the same verification script:

```bash
cd verification/week2-rerun-scene
./run.sh
```

Expected success markers:

```text
visualizer received final frame
Verified: Rerun Viewer recording was generated.
Verified: Rerun recording was generated.
```

The script first creates the saved `.rrd` recording, then starts a live Rerun
Viewer capture and runs the dataflow again so the video starts from the initial
scene instead of jumping directly to the final state.

## Desktop Capture Notes

The verification machine has a desktop session, but SSH shells do not always
inherit the desktop display. The script therefore tries the current `DISPLAY`,
then `:1`, then `:0`. In this verification run, `DISPLAY=:1` produced the Viewer
screenshot and short recording.

If there is no desktop display, Rerun may report:

```text
neither WAYLAND_DISPLAY nor WAYLAND_SOCKET nor DISPLAY is set
```

That is expected on headless hosts. Open the generated `.rrd` later on a desktop
machine, or use a virtual display if your environment allows it.

## Reproduction Tips

- Capture only the Rerun Viewer window when recording tutorial media; full
  desktop recordings are harder to read.
- Add an initial hold before motion starts, otherwise the recording may begin
  after the actors have already moved.
- Keep `RERUN_ANALYTICS=disabled` in tutorial scripts when you want clean,
  non-interactive logs.
- Do not commit `.rrd` recordings unless they are intentionally small. They can
  grow quickly once you add images or sensor data.
- If `dora run --uv` cannot find `uv`, install `uv` inside the virtual
  environment or remove `--uv` and run plain Python nodes.

## What to Try Next

Good next experiments are:

- Add path lines in Rerun so the planned route is visible.
- Split the controller into separate robot and car nodes.
- Replace the synthetic trajectory with real robot state from another Dora node.
- Add a camera stream or sensor feedback in a later chapter.
