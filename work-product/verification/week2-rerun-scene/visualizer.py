import json
import os
from pathlib import Path

import rerun as rr
import rerun.blueprint as rrb
from dora import Node


ARTIFACTS = Path("artifacts")
MODELS = Path("models")
ARTIFACTS.mkdir(exist_ok=True)

BLUEPRINT = rrb.Blueprint(
    rrb.Spatial3DView(origin="/world", name="Dora Rerun obstacle course"),
    rrb.TimePanel(timeline="frame", fps=30.0),
    rrb.BlueprintPanel(state="collapsed"),
    rrb.SelectionPanel(state="collapsed"),
    auto_views=False,
)

rr.init("dora_rerun_obstacle_course", default_blueprint=BLUEPRINT)
if os.environ.get("RERUN_LIVE") == "1":
    rr.connect_grpc("rerun+http://127.0.0.1:9876/proxy", default_blueprint=BLUEPRINT)
else:
    rr.save(str(ARTIFACTS / "dora_rerun_scene.rrd"))
rr.send_blueprint(
    BLUEPRINT
)

node = Node()


def _log_static_scene() -> None:
    rr.log("world", rr.ViewCoordinates.RIGHT_HAND_Z_UP, static=True)
    rr.log(
        "world/floor",
        rr.Boxes3D(
            centers=[[0.0, 0.0, -0.04]],
            half_sizes=[[4.9, 2.4, 0.03]],
            colors=[(230, 236, 232)],
            labels=["floor"],
        ),
        static=True,
    )
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
    rr.log(
        "world/actors/robot",
        rr.Asset3D(path=MODELS / "humanoid_robot.gltf"),
        static=True,
    )
    rr.log(
        "world/actors/car",
        rr.Asset3D(path=MODELS / "small_car.gltf"),
        static=True,
    )


def _log_actor_transform(prefix: str, x: float, y: float, heading: float) -> None:
    rr.log(
        prefix,
        rr.Transform3D(
            translation=[x, y, 0.0],
            rotation=rr.RotationAxisAngle(axis=[0.0, 0.0, 1.0], radians=heading),
        ),
    )


def _log_state(state: dict) -> None:
    frame = int(state["frame"])
    rr.set_time("frame", sequence=frame)

    robot = state["objects"]["robot"]
    car = state["objects"]["car"]

    rx, ry = robot["x"], robot["y"]
    cx, cy = car["x"], car["y"]

    _log_actor_transform("world/actors/robot", rx, ry, robot["heading"])
    _log_actor_transform("world/actors/car", cx, cy, car["heading"])


_log_static_scene()

for event in node:
    if event["type"] == "INPUT":
        state = json.loads(event["value"][0].as_py())
        _log_state(state)
        if state["frame"] == state["total_frames"] - 1:
            print("visualizer received final frame")
    elif event["type"] == "STOP":
        break
