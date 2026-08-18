# Dora-Controlled Motion in a Rerun Scene

## Version Information

| Component | Version / Environment |
| --- | --- |
| Operating system | Ubuntu 22.04.5 LTS, x86_64 |
| Python | CPython 3.11.14 |
| Dora CLI | 1.0.0-rc.4 |
| dora-rs Python package | `dora-rs==1.0.0rc4` |
| Rerun CLI and Python SDK | 0.33.0 |
| uv | 0.11.17 |
| pyarrow | 24.0.0 |
| PyYAML | 6.0.3 |

## Downloads

- [Complete Rerun and Dora reference project](../assets/week2-rerun-scene/rerun-scene-reference.zip)

This is the same fixed scene, model, trajectory, and Dora project introduced in
the previous chapter.

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

## Choose a Build Route

<div class="prompt-route prompt-route--create">
  <span class="prompt-route__label">Create route</span>
  <strong>Add Dora-controlled motion to the static scene</strong>
  <p>Use this to design the dataflow, state contract, and trajectories yourself.</p>
</div>

```text
Starting from the static Rerun scene specification, create a Dora 1.0.0-rc.4
dataflow with separate controller and visualizer nodes. Define one structured
scene-state output containing frame index plus robot and car transforms. Design
collision-free deterministic trajectories: the humanoid starts first, each
actor goes around the cube, approaches the cylinder, and stops; the car starts
later so the motion is easy to read.

Keep Rerun at 0.33.0 and preserve all static coordinates and model scale. Add
trajectory tests, a single run entry, an RRD output, and a 960x540 H.264 Viewer
recording that begins at the initial positions and reaches both final waypoints.
Verify runtime markers and artifacts before reporting success.
```

<div class="prompt-route prompt-route--reproduce">
  <span class="prompt-route__label">Reproduce route</span>
  <strong>Run the verified Dora motion project</strong>
  <p>Use this to focus on how Dora drives an existing scene.</p>
</div>

```text
Use the supplied Rerun and Dora project without changing models, coordinates,
paths, versions, or scripts. Read VERSIONS.md, TUTORIAL_CONTRACT.md,
ASSET_GUIDE.md, and READER_PROMPT.md. Report the only entry and acceptance
markers, run it once, and inspect controller/visualizer runtime markers, the
non-empty RRD, the recording dimensions and duration, final waypoints, and git
status. A zero exit code alone is not success.
```

## Inspect the Dora-Controlled Motion

Continue with the reference project downloaded above. The motion implementation
is already included, so ask the assistant to explain and verify it without
changing the scene or model assets:

```text
Inspect the supplied Dora-controlled Rerun reference project.

Do not replace the glTF files, change object coordinates, redesign the paths,
or regenerate the scene. Explain how dataflow.yml connects controller.py and
visualizer.py, how trajectory.py delays and sequences the two actors, and how
run.sh creates the .rrd output.

Run the focused source checks, then run `bash run.sh`. Confirm that the recording
starts at the initial positions, both actors reach their final waypoints, and
artifacts/dora_rerun_scene.rrd is non-empty. Report errors and sanitized
version information without printing identity, network, or secret data.
```

The fixed source removes scene-generation differences while preserving the
useful assistant workflow: inspect the dataflow, run it, diagnose failures, and
verify the result.

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
cd rerun-scene-reference
bash run.sh
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

## Complete Motion Source

The complete text sources are shown directly below. The reference archive also
contains the glTF files and Viewer capture script.

### `dataflow.yml`

```yaml
{{#include ../assets/week2-rerun-scene/source/dataflow.yml}}
```

### `trajectory.py`

```python
{{#include ../assets/week2-rerun-scene/source/trajectory.py}}
```

### `controller.py`

```python
{{#include ../assets/week2-rerun-scene/source/controller.py}}
```

### `visualizer.py`

```python
{{#include ../assets/week2-rerun-scene/source/visualizer.py}}
```

### `run.sh`

```bash
{{#include ../assets/week2-rerun-scene/source/run.sh}}
```

## Desktop Capture Notes

An SSH shell does not always inherit the active desktop display. The script
therefore tries the current `DISPLAY`, then `:1`, then `:0`. If the Viewer does
not open, set `DISPLAY` to the active desktop session explicitly and rerun the
capture.

If there is no desktop display, Rerun may report:

```text
neither WAYLAND_DISPLAY nor WAYLAND_SOCKET nor DISPLAY is set
```

That is expected on headless hosts. Open the generated `.rrd` later on a desktop
machine, or use a virtual display if your environment allows it.

## Next Step

The next chapter moves from Rerun visualization to Habitat-Sim simulation and builds a wrist camera example that produces RGB and depth data.
