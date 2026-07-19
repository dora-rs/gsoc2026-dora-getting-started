from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import cv2
import habitat_sim
import magnum as mn
import numpy as np
import quaternion
import trimesh
from habitat_sim import AgentState, CameraSensorSpec, Configuration, SensorSubType, SensorType
from habitat_sim.physics import MotionType


ROOT = Path(__file__).resolve().parent
WIDTH = 960
HEIGHT = 540
FPS = 12
CUBE_SIZE = 0.10
PANDA_HOME = np.array(
    [0.0, -0.68, 0.0, -2.18, 0.0, 1.70, 0.78], dtype=np.float64
)
PANDA_URDF = ROOT / "assets" / "franka_panda_with_wrist_camera.urdf"
WRIST_CAMERA_LINK = "wrist_camera_link"
WORLD_UP = np.array([0.0, 1.0, 0.0], dtype=np.float64)
CUBE_CENTERS = {
    "red": np.array([0.72, CUBE_SIZE / 2.0, 0.18], dtype=np.float64),
    "yellow": np.array([0.72, CUBE_SIZE / 2.0, 0.00], dtype=np.float64),
    "blue": np.array([0.72, CUBE_SIZE / 2.0, -0.18], dtype=np.float64),
}
COLORS = {
    "red": (230, 38, 45, 255),
    "yellow": (242, 204, 35, 255),
    "blue": (38, 96, 224, 255),
}


def make_box(
    extents: tuple[float, float, float],
    translation: tuple[float, float, float],
    color: tuple[int, int, int, int],
) -> trimesh.Trimesh:
    mesh = trimesh.creation.box(extents=extents)
    mesh.apply_translation(translation)
    mesh.visual = trimesh.visual.TextureVisuals(
        material=trimesh.visual.material.PBRMaterial(
            baseColorFactor=[channel / 255.0 for channel in color],
            metallicFactor=0.02,
            roughnessFactor=0.55,
        )
    )
    return mesh


def prepare_runtime_assets(
    asset_dir: Path,
) -> tuple[Path, dict[str, Path]]:
    asset_dir.mkdir(parents=True, exist_ok=True)
    floor_path = asset_dir / "floor.glb"
    floor = make_box((3.0, 3.0, 0.04), (0.3, 0.0, -0.02), (112, 118, 124, 255))
    trimesh.Scene([floor]).export(floor_path)

    cube_paths: dict[str, Path] = {}
    for name, color in COLORS.items():
        path = asset_dir / f"{name}_cube.glb"
        cube = make_box((CUBE_SIZE, CUBE_SIZE, CUBE_SIZE), (0.0, 0.0, 0.0), color)
        trimesh.Scene([cube]).export(path)
        cube_paths[name] = path
    return floor_path, cube_paths


def sensor_spec(
    uuid: str, resolution: list[int], hfov: float
) -> CameraSensorSpec:
    spec = CameraSensorSpec()
    spec.uuid = uuid
    spec.sensor_type = SensorType.COLOR
    spec.sensor_subtype = SensorSubType.PINHOLE
    spec.resolution = resolution
    spec.position = [0.0, 0.0, 0.0]
    spec.orientation = [0.0, 0.0, 0.0]
    spec.hfov = hfov
    return spec


def create_simulator(floor_path: Path) -> habitat_sim.Simulator:
    backend = habitat_sim.SimulatorConfiguration()
    backend.scene_id = str(floor_path)
    backend.gpu_device_id = 0
    backend.enable_physics = True
    agent = habitat_sim.agent.AgentConfiguration()
    agent.sensor_specifications = [
        sensor_spec("overview", [HEIGHT, WIDTH], 75.0),
        sensor_spec("wrist", [HEIGHT, WIDTH], 95.0),
    ]
    return habitat_sim.Simulator(Configuration(backend, [agent]))


def matrix_to_numpy(matrix: mn.Matrix4) -> tuple[np.ndarray, np.ndarray]:
    position = np.array([float(matrix.translation[i]) for i in range(3)])
    rotation = np.array(
        [[float(matrix.rotation()[col][row]) for col in range(3)] for row in range(3)]
    )
    return position, rotation


def look_at_rotation(position: np.ndarray, target: np.ndarray) -> np.quaternion:
    forward = target - position
    forward /= np.linalg.norm(forward)
    up_guess = WORLD_UP
    if abs(float(np.dot(forward, up_guess))) > 0.98:
        up_guess = np.array([0.0, 0.0, 1.0], dtype=np.float64)
    right = np.cross(forward, up_guess)
    right /= np.linalg.norm(right)
    up = np.cross(right, forward)
    up /= np.linalg.norm(up)
    rotation = np.eye(3)
    rotation[:, 0] = right
    rotation[:, 1] = up
    rotation[:, 2] = -forward
    return quaternion.from_rotation_matrix(rotation)


def load_articulated_arm(sim: habitat_sim.Simulator, urdf_path: Path):
    manager = sim.get_articulated_object_manager()
    arm = manager.add_articulated_object_from_urdf(str(urdf_path), fixed_base=True)
    if arm is None:
        raise RuntimeError(f"failed to load Panda URDF: {urdf_path}")
    arm.motion_type = MotionType.KINEMATIC
    arm.transformation = mn.Matrix4.rotation_x(mn.Rad(-math.pi / 2.0))
    return arm


def set_camera(agent: habitat_sim.Agent, position: np.ndarray, rotation: np.quaternion) -> None:
    state = AgentState()
    state.position = np.asarray(position, dtype=np.float32)
    state.rotation = rotation
    agent.set_state(state, reset_sensors=True)


def rgb_observation(sim: habitat_sim.Simulator, sensor_uuid: str) -> np.ndarray:
    image = np.asarray(sim.get_sensor_observations()[sensor_uuid])
    if image.shape[-1] == 4:
        image = image[:, :, :3]
    return np.ascontiguousarray(image)


@dataclass
class PickPlaceScene:
    sim: habitat_sim.Simulator
    agent: habitat_sim.Agent
    arm: object
    cubes: dict[str, object]
    hand_link_id: int

    @classmethod
    def create(cls, output_dir: Path) -> "PickPlaceScene":
        floor_path, cube_paths = prepare_runtime_assets(output_dir / "runtime-assets")
        sim = create_simulator(floor_path)
        agent = sim.initialize_agent(0)
        arm = load_articulated_arm(sim, PANDA_URDF)
        arm.joint_positions = PANDA_HOME.astype(np.float32)

        template_manager = sim.get_object_template_manager()
        rigid_manager = sim.get_rigid_object_manager()
        cubes = {}
        for name, path in cube_paths.items():
            template = template_manager.create_new_template(str(path), False)
            template.render_asset_handle = str(path)
            template.collision_asset_handle = str(path)
            template.mass = 0.2
            template.friction_coefficient = 0.9
            template.restitution_coefficient = 0.0
            template_id = template_manager.register_template(template, f"{name}_cube")
            cube = rigid_manager.add_object_by_template_id(template_id)
            cube.motion_type = MotionType.KINEMATIC
            cube.translation = mn.Vector3(*CUBE_CENTERS[name])
            cubes[name] = cube

        sim.step_physics(1.0 / FPS)
        hand_link_id = arm.get_link_id_from_name("panda_hand")
        if hand_link_id < 0:
            raise RuntimeError("panda_hand link was not found")
        wrist_link_id = arm.get_link_id_from_name(WRIST_CAMERA_LINK)
        if wrist_link_id < 0:
            raise RuntimeError("wrist camera link was not found")
        return cls(sim, agent, arm, cubes, hand_link_id)

    def close(self) -> None:
        self.sim.close()

    def hand_transform(self) -> mn.Matrix4:
        return self.arm.get_link_scene_node(
            self.hand_link_id
        ).absolute_transformation()

    def set_joints(self, joints: np.ndarray) -> None:
        self.arm.joint_positions = np.asarray(joints, dtype=np.float32)
        self.sim.step_physics(1.0 / FPS)

    def set_cube_center(self, name: str, center: np.ndarray) -> None:
        self.cubes[name].translation = mn.Vector3(*np.asarray(center, dtype=np.float64))

    def cube_center(self, name: str) -> np.ndarray:
        value = self.cubes[name].translation
        return np.array([float(value[i]) for i in range(3)], dtype=np.float64)

    def render_wrist(self) -> np.ndarray:
        transform = self.arm.get_link_scene_node(
            self.arm.get_link_id_from_name(WRIST_CAMERA_LINK)
        ).absolute_transformation()
        position, _rotation_matrix = matrix_to_numpy(transform)
        task_focus = self.cube_center("red")
        set_camera(self.agent, position, look_at_rotation(position, task_focus))
        return cv2.flip(rgb_observation(self.sim, "wrist"), 1)

    def render_overview(self) -> np.ndarray:
        position = np.array([1.40, 1.25, 1.15], dtype=np.float64)
        target = np.array([0.40, 0.28, 0.0], dtype=np.float64)
        set_camera(self.agent, position, look_at_rotation(position, target))
        return rgb_observation(self.sim, "overview")

    def attach_red_to_hand(self) -> mn.Matrix4:
        red_transform = self.cubes["red"].transformation
        return self.hand_transform().inverted() @ red_transform

    def update_attached_red(self, relative_transform: mn.Matrix4) -> None:
        self.cubes["red"].transformation = self.hand_transform() @ relative_transform

    def place_red_on_blue(self) -> None:
        blue = self.cube_center("blue")
        self.set_cube_center("red", blue + np.array([0.0, CUBE_SIZE, 0.0]))


def color_pixel_counts(rgb: np.ndarray) -> dict[str, int]:
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    masks = {
        "red": cv2.inRange(hsv, (0, 90, 70), (12, 255, 255))
        + cv2.inRange(hsv, (170, 90, 70), (179, 255, 255)),
        "yellow": cv2.inRange(hsv, (18, 80, 70), (38, 255, 255)),
        "blue": cv2.inRange(hsv, (95, 80, 50), (135, 255, 255)),
    }
    return {name: int(np.count_nonzero(mask)) for name, mask in masks.items()}
