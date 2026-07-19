# Rerun Introduction and Static Scene

## Version Information

| Component | Version / Environment |
| --- | --- |
| Operating system | Ubuntu 22.04.5 LTS, x86_64 |
| Python | CPython 3.10.12 |
| Rerun CLI and Python SDK | 0.33.0 |

## Goal

This chapter creates the static foundation for the scene used in the next
chapter:

- A floor plane.
- A cube obstacle.
- A cylinder goal.
- A reusable glTF humanoid robot model.
- A reusable glTF small car model.
- A Rerun Viewer screenshot that proves the scene can be inspected visually.

The robot and car do not move in this chapter. Keeping the first Rerun example
static makes it easier to understand the coordinate system, scene hierarchy,
assets, and Viewer workflow before adding Dora-controlled motion.

![Rerun Viewer static scene screenshot](../assets/week2-rerun-scene/rerun_viewer_screenshot.png)

## What Rerun Is

Rerun is a visualization and logging toolkit for robotics, computer vision, and
physical AI systems. A program records typed data such as transforms, boxes,
images, points, text, tensors, and time-series state. The Rerun Viewer can show
that data live, or open a saved `.rrd` recording later.

The official Python SDK package is `rerun-sdk`, and the Python import name is
`rerun`. Installing the Python SDK also provides the Viewer command line tool.

`rerun-sdk==0.33.0` requires Python 3.10 or newer. Wheels for this version are
available for Windows x86-64, Linux x86-64, Linux ARM64, and macOS ARM64. If
your platform is not covered by a wheel, use the official Rerun installation
and troubleshooting pages as the source of truth.

## Prepare the Static Scene

Start Codex CLI from the tutorial root and give it a prompt like this:

```text
I want to create a small static Rerun scene for a Dora tutorial.

Please search the latest official Rerun documentation and PyPI package page
before choosing commands or APIs. Use a local isolated Python environment. Do not
expose secrets, private hostnames, tokens, or absolute home paths in committed
files or tutorial text.

Target:
- Install the latest stable rerun-sdk package that works on this machine.
- Create a script that logs a 3D scene to Rerun.
- The scene should contain a floor, a cube obstacle, a cylinder goal, a humanoid
  robot model, and a small car model.
- Use reusable glTF model assets for the robot and car.
- Save a .rrd recording.
- Save a static screenshot from the Rerun Viewer for the tutorial when a desktop
  session is available.

Please create a run script that:
1. Creates or reuses a virtual environment.
2. Installs pinned dependencies.
3. Prints OS, Python, Rerun, and key package versions.
4. Generates the model assets if needed.
5. Logs the static scene.
6. Fails if the Rerun recording was not created.

After running it, summarize any errors and update the reproduction notes so a
student is less likely to hit the same problem.
```

The important details in the prompt are:

- Ask for official documentation before choosing package names or APIs.
- Keep a pinned, reproducible Python environment.
- Use real Rerun Viewer output, not a hand-drawn illustration.
- Use reusable 3D assets instead of one-off primitive-only placeholders.

## Project Layout

The runnable example lives in:

```text
verification/week2-rerun-scene/
├── generate_models.py
├── models/
├── requirements.txt
├── run.sh
└── visualizer.py
```

The next chapter extends the same example directory with Dora nodes and
motion capture. Generated runtime files stay out of the tutorial source:

- `.venv/` contains the local Python environment.
- `models/` contains reusable glTF assets for the humanoid robot and small car.
- `artifacts/` contains generated `.rrd` files and any local Viewer media.
- `logs/` contains runtime logs.
- `out/` contains Dora runtime session data.

Curated Rerun Viewer media files are copied into `src/assets/` so the book can
render them.

## Dependencies

The static Rerun portion uses:

```text
rerun-sdk==0.33.0
```

Pinning versions is useful in a tutorial because it makes bugs easier to
reproduce. When you intentionally update a dependency, update the version
information at the top of the chapter and run the verification script again.

## Log Static Objects

The Rerun scene starts with a world coordinate system and a few static objects.
Static data is logged once and then reused across the recording.

```python
import rerun as rr

rr.init("dora_rerun_obstacle_course")
rr.save("artifacts/dora_rerun_scene.rrd")

rr.log("world", rr.ViewCoordinates.RIGHT_HAND_Z_UP, static=True)
rr.log(
    "world/obstacles/cube",
    rr.Boxes3D(
        centers=[[0.0, 0.0, 0.5]],
        half_sizes=[[0.5, 0.5, 0.5]],
        colors=[(190, 74, 58)],
        labels=["cube obstacle"],
        fill_mode="solid",
    ),
    static=True,
)
rr.log(
    "world/goal/cylinder",
    rr.Cylinders3D(
        centers=[[4.0, 0.0, 0.5]],
        lengths=[1.0],
        radii=[0.35],
        colors=[(45, 127, 111)],
        labels=["goal cylinder"],
    ),
    static=True,
)
```

The full `visualizer.py` also logs the floor, robot model, and car model under a
clear hierarchy:

```text
world/
├── floor
├── obstacles/cube
├── goal/cylinder
└── actors/
    ├── robot
    └── car
```

## Add Reusable glTF Assets

The robot and car are logged as glTF assets:

```python
from pathlib import Path

import rerun as rr

MODELS = Path("models")

rr.log("world/actors/robot", rr.Asset3D(path=MODELS / "humanoid_robot.gltf"), static=True)
rr.log("world/actors/car", rr.Asset3D(path=MODELS / "small_car.gltf"), static=True)
```

For this tutorial, glTF worked better than OBJ/MTL. OBJ was easy to generate,
but the Rerun Viewer rendered the model as a white material in this environment.
The glTF assets carried materials more reliably.

## Run the Static Scene

On Linux or an SSH machine with a desktop session:

```bash
cd verification/week2-rerun-scene
./run.sh
```

The script creates `.venv`, installs dependencies, generates the glTF models,
saves the `.rrd`, and prints the verified versions.

Expected success markers include:

```text
Verified: Rerun recording was generated.
```

If there is no desktop display, keep the generated `.rrd` and open it later on a
desktop machine:

```bash
cd verification/week2-rerun-scene
source .venv/bin/activate
rerun artifacts/dora_rerun_scene.rrd
```

## Next Step

The next chapter keeps this scene layout and uses Dora to publish changing
robot and car transforms. That turns the static Rerun scene into a small
Dora-controlled motion example.
