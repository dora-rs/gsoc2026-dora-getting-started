from pathlib import Path

import rerun as rr
import rerun.blueprint as rrb


ARTIFACTS = Path("artifacts")
MODELS = Path("models")
ARTIFACTS.mkdir(exist_ok=True)

BLUEPRINT = rrb.Blueprint(
    rrb.Spatial3DView(origin="/world", name="Rerun static obstacle course"),
    rrb.BlueprintPanel(state="collapsed"),
    rrb.SelectionPanel(state="collapsed"),
    auto_views=False,
)

rr.init("dora_rerun_obstacle_course", default_blueprint=BLUEPRINT)
rr.save(str(ARTIFACTS / "dora_rerun_scene.rrd"))
rr.send_blueprint(BLUEPRINT)

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
rr.log("world/actors/robot", rr.Asset3D(path=MODELS / "humanoid_robot.gltf"), static=True)
rr.log("world/actors/car", rr.Asset3D(path=MODELS / "small_car.gltf"), static=True)

print("Verified: static Rerun scene was logged.")

