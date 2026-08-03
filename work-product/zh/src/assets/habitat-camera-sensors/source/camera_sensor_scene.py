#!/usr/bin/env python3
"""
Habitat-Sim wrist camera sensor example.

This example creates a simple simulated scene, loads a Franka Panda URDF arm,
renders RGB/depth from a camera link fixed to the Panda hand, shows external
RGB/depth windows, and writes local verification outputs under ./outputs.
"""

from __future__ import annotations

import argparse
import math
import os
import subprocess
import sys
from pathlib import Path

import cv2
import habitat_sim
import magnum as mn
import numpy as np
import quaternion
import trimesh
from habitat_sim import AgentState, CameraSensorSpec, Configuration, SensorSubType, SensorType
from habitat_sim.physics import MotionType


WIDTH = 640
HEIGHT = 480
FPS = 20
FRAMES = 220
PANDA_URDF = "franka_panda_with_wrist_camera.urdf"
WRIST_CAMERA_LINK = "wrist_camera_link"
PANDA_HOME = np.array([0.0, -0.68, 0.0, -2.18, 0.0, 1.70, 0.78], dtype=np.float32)
WORLD_UP = np.array([0.0, 1.0, 0.0], dtype=np.float64)
FLOOR_Y = 0.0
MIN_CAMERA_HEIGHT = 0.30
MIN_GROUND_HIT_DISTANCE = 0.75


def log_environment() -> str:
    lines = [
        f"python: {sys.version.split()[0]}",
        f"habitat_sim: {getattr(habitat_sim, '__version__', 'unknown')}",
        f"opencv: {cv2.__version__}",
        f"numpy: {np.__version__}",
        f"trimesh: {trimesh.__version__}",
        f"DISPLAY: {os.environ.get('DISPLAY', '<unset>')}",
    ]
    try:
        smi = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,driver_version,memory.total",
                "--format=csv,noheader",
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        lines.append(f"nvidia-smi: {smi.stdout.strip() or 'no output'}")
    except FileNotFoundError:
        lines.append("nvidia-smi: missing")
    return "\n".join(lines) + "\n"


def make_box(extents: tuple[float, float, float], translation: tuple[float, float, float], color: tuple[int, int, int, int]) -> trimesh.Trimesh:
    mesh = trimesh.creation.box(extents=extents)
    mesh.apply_translation(translation)
    mesh.visual = trimesh.visual.TextureVisuals(
        material=trimesh.visual.material.PBRMaterial(
            baseColorFactor=[c / 255.0 for c in color],
            metallicFactor=0.0,
            roughnessFactor=0.65,
        )
    )
    return mesh


def habitat_to_scene_point(point: np.ndarray) -> tuple[float, float, float]:
    # Trimesh authors this GLB in Z-up coordinates; Habitat imports it into a Y-up world.
    return (float(point[0]), float(-point[2]), float(point[1]))


def create_scene(scene_path: Path, cube_centers: list[tuple[float, float, float]] | None = None) -> None:
    # Source mesh is authored Z-up. The GLB import path maps it into Habitat's Y-up world.
    floor = make_box((80.0, 80.0, 0.04), (0.0, 0.0, -0.02), (120, 120, 120, 255))

    cubes: list[trimesh.Trimesh] = []
    if cube_centers:
        colors = [
            (230, 40, 40, 255),
            (40, 220, 70, 255),
            (40, 100, 240, 255),
            (235, 210, 40, 255),
        ]
        sizes = [(0.12, 0.12, 0.12), (0.12, 0.12, 0.12), (0.12, 0.12, 0.12), (0.10, 0.10, 0.10)]
        for center, color, size in zip(cube_centers, colors, sizes):
            cubes.append(make_box(size, habitat_to_scene_point(np.array(center, dtype=np.float64)), color))

    scene = trimesh.Scene()
    for idx, mesh in enumerate([floor, *cubes]):
        scene.add_geometry(mesh, node_name=f"part_{idx}", geom_name=f"part_{idx}")
    scene.export(scene_path)


def sensor_spec(uuid: str, sensor_type: SensorType) -> CameraSensorSpec:
    spec = CameraSensorSpec()
    spec.uuid = uuid
    spec.sensor_type = sensor_type
    spec.sensor_subtype = SensorSubType.PINHOLE
    spec.resolution = [HEIGHT, WIDTH]
    spec.position = [0.0, 0.0, 0.0]
    spec.orientation = [0.0, 0.0, 0.0]
    return spec


def make_sim(scene_path: Path) -> habitat_sim.Simulator:
    backend = habitat_sim.SimulatorConfiguration()
    backend.scene_id = str(scene_path)
    backend.gpu_device_id = 0
    backend.enable_physics = True

    agent_cfg = habitat_sim.agent.AgentConfiguration()
    agent_cfg.sensor_specifications = [
        sensor_spec("color", SensorType.COLOR),
        sensor_spec("depth", SensorType.DEPTH),
    ]
    return habitat_sim.Simulator(Configuration(backend, [agent_cfg]))


def load_articulated_arm(sim: habitat_sim.Simulator, urdf_path: Path):
    manager = sim.get_articulated_object_manager()
    arm = manager.add_articulated_object_from_urdf(str(urdf_path), fixed_base=True)
    if arm is None:
        raise RuntimeError(f"failed to load articulated arm URDF: {urdf_path}")
    arm.motion_type = MotionType.KINEMATIC
    arm.transformation = mn.Matrix4.rotation_x(mn.Rad(-math.pi / 2.0))
    return arm


def animate_arm(arm, frame: int) -> np.ndarray:
    t = frame / max(1, FRAMES - 1)
    phase = 2.0 * math.pi * t
    joints = PANDA_HOME + np.array(
        [
            0.04 * math.sin(phase),
            0.015 * math.sin(phase + 0.4),
            0.018 * math.sin(phase + 1.1),
            0.012 * math.sin(phase + 0.8),
            0.015 * math.sin(phase + 1.7),
            0.015 * math.sin(phase + 0.2),
            0.010 * math.sin(phase + 2.1),
        ],
        dtype=np.float32,
    )
    arm.joint_positions = joints
    return joints


def vector3_to_np(value) -> np.ndarray:
    return np.array([float(value[0]), float(value[1]), float(value[2])], dtype=np.float64)


def matrix3_to_np(value) -> np.ndarray:
    return np.array([[float(value[col][row]) for col in range(3)] for row in range(3)], dtype=np.float64)


def wrist_camera_pose_from_arm(arm) -> tuple[np.ndarray, np.quaternion, np.ndarray, np.ndarray, np.ndarray]:
    link_id = arm.get_link_id_from_name(WRIST_CAMERA_LINK)
    if link_id < 0:
        raise RuntimeError(f"URDF link `{WRIST_CAMERA_LINK}` not found")
    node = arm.get_link_scene_node(link_id)
    transform = node.absolute_transformation()
    position = vector3_to_np(transform.translation)
    rotation_matrix = matrix3_to_np(transform.rotation())
    rotation = quaternion.from_rotation_matrix(rotation_matrix)
    right = rotation_matrix[:, 0]
    up = rotation_matrix[:, 1]
    forward = -rotation_matrix[:, 2]
    return position, rotation, forward, right, up


def cube_centers_for_camera(position: np.ndarray, forward: np.ndarray, right: np.ndarray) -> list[tuple[float, float, float]]:
    forward = normalize(forward)
    horizontal_forward = forward.copy()
    horizontal_forward[1] = 0.0
    if np.linalg.norm(horizontal_forward) < 1e-6:
        horizontal_forward = np.array([1.0, 0.0, 0.0], dtype=np.float64)
    horizontal_forward = normalize(horizontal_forward)
    lateral = normalize(np.cross(WORLD_UP, horizontal_forward))

    cube_heights = [0.06, 0.06, 0.06, 0.05]
    target_height = 0.10
    if forward[1] < -0.15:
        distance = (position[1] - target_height) / max(0.2, -float(forward[1]))
        distance = float(np.clip(distance, 0.65, 1.15))
    else:
        distance = 0.95
    focus = position + forward * distance
    focus[1] = target_height
    centers = [
        focus - lateral * 0.20,
        focus,
        focus + lateral * 0.20,
        focus + horizontal_forward * 0.18 + lateral * 0.07,
    ]
    return [(float(c[0]), height, float(c[2])) for c, height in zip(centers, cube_heights)]


def prepare_scene_for_panda_camera(scene_path: Path, urdf_path: Path) -> list[tuple[float, float, float]]:
    create_scene(scene_path)
    sim = make_sim(scene_path)
    arm = load_articulated_arm(sim, urdf_path)
    arm.joint_positions = PANDA_HOME
    sim.step_physics(1.0 / FPS)
    position, _rotation, forward, right, _up = wrist_camera_pose_from_arm(arm)
    sim.close()
    cube_centers = cube_centers_for_camera(position, forward, right)
    create_scene(scene_path, cube_centers)
    return cube_centers


def normalize(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    if n < 1e-9:
        raise ValueError("cannot normalize near-zero vector")
    return v / n


def look_at_rotation(position: np.ndarray, target: np.ndarray) -> np.quaternion:
    forward = normalize(target - position)
    up_guess = WORLD_UP
    if abs(float(np.dot(forward, up_guess))) > 0.98:
        up_guess = np.array([0.0, 0.0, 1.0], dtype=np.float64)
    right = normalize(np.cross(forward, up_guess))
    up = normalize(np.cross(right, forward))
    rot = np.eye(3)
    rot[:, 0] = right
    rot[:, 1] = up
    rot[:, 2] = -forward
    return quaternion.from_rotation_matrix(rot)


def set_camera(agent: habitat_sim.Agent, position: np.ndarray, rotation: np.quaternion) -> None:
    state = AgentState()
    state.position = position.astype(np.float32)
    state.rotation = rotation
    agent.set_state(state, reset_sensors=True)


def observations_from_pose(sim: habitat_sim.Simulator, agent: habitat_sim.Agent, position: np.ndarray, rotation: np.quaternion) -> dict[str, np.ndarray]:
    set_camera(agent, position, rotation)
    return sim.get_sensor_observations()


def observations_from_look_at(sim: habitat_sim.Simulator, agent: habitat_sim.Agent, position: np.ndarray, target: np.ndarray) -> dict[str, np.ndarray]:
    set_camera(agent, position, look_at_rotation(position, target))
    return sim.get_sensor_observations()


def rgb_frame(color_obs: np.ndarray) -> np.ndarray:
    rgb = np.asarray(color_obs)
    if rgb.shape[-1] == 4:
        rgb = rgb[:, :, :3]
    return np.ascontiguousarray(rgb)


def depth_frame(depth_obs: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    depth = np.asarray(depth_obs, dtype=np.float32)
    depth_clipped = np.clip(depth, 0.0, 6.0)
    depth_norm = (255.0 * (1.0 - depth_clipped / 6.0)).astype(np.uint8)
    depth_color = cv2.applyColorMap(depth_norm, cv2.COLORMAP_TURBO)
    return depth, depth_color


def video_writer(path: Path, size: tuple[int, int]) -> cv2.VideoWriter:
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(path), fourcc, FPS, size)
    if not writer.isOpened():
        raise RuntimeError(f"failed to open video writer: {path}")
    return writer


def add_label(frame: np.ndarray, label: str) -> np.ndarray:
    out = frame.copy()
    cv2.rectangle(out, (10, 10), (10 + 12 * len(label), 42), (0, 0, 0), -1)
    cv2.putText(out, label, (18, 33), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2, cv2.LINE_AA)
    return out


def run_probe(show_windows: bool) -> None:
    root = Path(__file__).resolve().parent
    outputs = root / "outputs"
    screenshots = outputs / "screenshots"
    videos = outputs / "videos"
    assets = root / "assets"
    for path in (screenshots, videos, assets):
        path.mkdir(parents=True, exist_ok=True)

    scene_path = assets / "habitat_wrist_camera_probe.glb"
    urdf_path = assets / PANDA_URDF
    if not urdf_path.exists():
        raise FileNotFoundError(f"Franka Panda URDF not found: {urdf_path}")
    cube_centers = prepare_scene_for_panda_camera(scene_path, urdf_path)

    (outputs / "environment.txt").write_text(log_environment(), encoding="utf-8")

    sim = make_sim(scene_path)
    agent = sim.initialize_agent(0)
    arm = load_articulated_arm(sim, urdf_path)

    rgb_video = video_writer(videos / "external_rgb_stream.mp4", (WIDTH, HEIGHT))
    depth_video = video_writer(videos / "external_depth_stream.mp4", (WIDTH, HEIGHT))
    combined_video = video_writer(videos / "external_rgb_depth_side_by_side.mp4", (WIDTH * 2, HEIGHT))
    overview_video = video_writer(videos / "habitat_overview.mp4", (WIDTH, HEIGHT))

    overview_pos = np.array([1.35, 1.55, 1.25], dtype=np.float64)
    overview_target = np.array([0.55, 0.15, 0.05], dtype=np.float64)

    if show_windows:
        cv2.namedWindow("Habitat overview", cv2.WINDOW_NORMAL)
        cv2.namedWindow("Wrist RGB Camera", cv2.WINDOW_NORMAL)
        cv2.namedWindow("Wrist Depth Camera", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Habitat overview", WIDTH, HEIGHT)
        cv2.resizeWindow("Wrist RGB Camera", WIDTH, HEIGHT)
        cv2.resizeWindow("Wrist Depth Camera", WIDTH, HEIGHT)

    sample_depth_stats: list[str] = []
    sample_joint_stats: list[str] = []
    min_camera_height = math.inf
    min_ground_hit_distance = math.inf

    for frame_idx in range(FRAMES):
        joints = animate_arm(arm, frame_idx)
        sim.step_physics(1.0 / FPS)

        overview_obs = observations_from_look_at(sim, agent, overview_pos, overview_target)
        overview_rgb = add_label(rgb_frame(overview_obs["color"]), "Franka Panda in Habitat-Sim")

        wrist_pos, wrist_rotation, wrist_forward, _wrist_right, _wrist_up = wrist_camera_pose_from_arm(arm)
        min_camera_height = min(min_camera_height, float(wrist_pos[1] - FLOOR_Y))
        if wrist_forward[1] < -1e-6:
            ground_hit_distance = float((wrist_pos[1] - FLOOR_Y) / -wrist_forward[1])
            min_ground_hit_distance = min(min_ground_hit_distance, ground_hit_distance)
        else:
            ground_hit_distance = math.inf
        wrist_obs = observations_from_pose(sim, agent, wrist_pos, wrist_rotation)
        wrist_rgb = add_label(rgb_frame(wrist_obs["color"]), "Panda wrist camera: RGB")
        wrist_depth_raw, wrist_depth_color = depth_frame(wrist_obs["depth"])
        wrist_depth_color = add_label(wrist_depth_color, "Panda wrist camera: depth")

        combined = np.hstack([wrist_rgb, cv2.cvtColor(wrist_depth_color, cv2.COLOR_BGR2RGB)])

        # OpenCV display expects BGR.
        overview_bgr = cv2.cvtColor(overview_rgb, cv2.COLOR_RGB2BGR)
        wrist_bgr = cv2.cvtColor(wrist_rgb, cv2.COLOR_RGB2BGR)
        combined_bgr = cv2.cvtColor(combined, cv2.COLOR_RGB2BGR)

        overview_video.write(overview_bgr)
        rgb_video.write(wrist_bgr)
        depth_video.write(wrist_depth_color)
        combined_video.write(combined_bgr)

        if frame_idx == 35:
            cv2.imwrite(str(screenshots / "habitat_overview.png"), overview_bgr)
            cv2.imwrite(str(screenshots / "external_rgb_window.png"), wrist_bgr)
            cv2.imwrite(str(screenshots / "external_depth_window.png"), wrist_depth_color)
            np.save(screenshots / "wrist_depth_raw_frame.npy", wrist_depth_raw)

        if frame_idx % 55 == 0:
            finite = wrist_depth_raw[np.isfinite(wrist_depth_raw)]
            sample_depth_stats.append(
                f"frame={frame_idx} wrist={wrist_pos.round(3).tolist()} "
                f"forward={wrist_forward.round(3).tolist()} "
                f"ground_hit_dist={ground_hit_distance:.3f} "
                f"depth_min={float(finite.min()):.3f} depth_max={float(finite.max()):.3f}"
            )
            sample_joint_stats.append(
                f"frame={frame_idx} joints_rad={joints.round(3).tolist()}"
            )

        if show_windows:
            cv2.imshow("Habitat overview", overview_bgr)
            cv2.imshow("Wrist RGB Camera", wrist_bgr)
            cv2.imshow("Wrist Depth Camera", wrist_depth_color)
            key = cv2.waitKey(int(1000 / FPS)) & 0xFF
            if key in (27, ord("q")):
                break

    for writer in (rgb_video, depth_video, combined_video, overview_video):
        writer.release()
    if show_windows:
        cv2.destroyAllWindows()
    sim.close()

    if min_camera_height < MIN_CAMERA_HEIGHT:
        raise RuntimeError(f"wrist camera dropped too close to the floor: min_height={min_camera_height:.3f}")
    if min_ground_hit_distance < MIN_GROUND_HIT_DISTANCE:
        raise RuntimeError(
            "wrist camera optical axis intersects the floor too close to the camera: "
            f"min_ground_hit_distance={min_ground_hit_distance:.3f}"
        )

    notes = [
        "# Habitat-Sim Sensor Probe Notes",
        "",
        "Status: outputs generated by the downloaded reference project.",
        "",
        "Verified outputs:",
        "- GPU Habitat-Sim scene render: `outputs/screenshots/habitat_overview.png`",
        "- External RGB stream screenshot: `outputs/screenshots/external_rgb_window.png`",
        "- External depth stream screenshot: `outputs/screenshots/external_depth_window.png`",
        "- RGB stream video: `outputs/videos/external_rgb_stream.mp4`",
        "- Depth stream video: `outputs/videos/external_depth_stream.mp4`",
        "- Side-by-side RGB/depth video: `outputs/videos/external_rgb_depth_side_by_side.mp4`",
        "- Overview video: `outputs/videos/habitat_overview.mp4`",
        "",
        "Scene contents:",
        "- Grey floor.",
        f"- Franka Panda arm loaded from `assets/{PANDA_URDF}`.",
        "- Visual meshes from the Franka ROS `franka_description` package.",
        "- Habitat world coordinates are treated as Y-up; the Panda URDF root is rotated from Z-up into that world.",
        "- Animated seven revolute Panda joints.",
        f"- Wrist camera pose bound to the full `{WRIST_CAMERA_LINK}` transform.",
        f"- Camera trajectory guard: min_height={min_camera_height:.3f}m, min_ground_hit_distance={min_ground_hit_distance:.3f}m.",
        f"- Colored cubes placed from the nominal wrist camera ray in Habitat coordinates: {np.array(cube_centers).round(3).tolist()}.",
        "",
        "Depth samples:",
        *sample_depth_stats,
        "",
        "Joint samples:",
        *sample_joint_stats,
        "",
    ]
    (outputs / "RUN_NOTES.md").write_text("\n".join(notes), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-windows", action="store_true", help="Render and save files without opening OpenCV windows.")
    args = parser.parse_args()
    run_probe(show_windows=not args.no_windows)


if __name__ == "__main__":
    main()
