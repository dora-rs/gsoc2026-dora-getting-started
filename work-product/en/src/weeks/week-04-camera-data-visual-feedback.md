# Camera Sensors in a Simulated Scene

## Version Information

This chapter was verified on a Linux desktop environment with GPU rendering.

- Operating system: Ubuntu 22.04.5 LTS, x86_64
- Python: CPython 3.9.23
- Habitat-Sim: 0.3.3
- OpenCV: 4.12.0
- NumPy: 1.26.4
- Trimesh: 4.7.4
- GPU: NVIDIA GeForce RTX 5090 Laptop GPU
- NVIDIA driver: 580.159.03

## What Habitat-Sim Is

Habitat-Sim is a simulator. It creates a virtual 3D world and renders sensor
observations from that world, including RGB camera images and depth images. That
is the missing piece when you want a robotics tutorial to use sensor data
without first building a physical test scene.

This is different from Rerun. Rerun is a visualization and logging tool: it can
display robot poses, maps, point clouds, images, planned paths, trajectories,
and status values. It does not create the physical world or generate camera data
by itself. In a complete stack, Habitat-Sim can produce sensor observations,
Dora can move those observations through a dataflow, and Rerun can display or
record the resulting state.

## Goal

This chapter builds a small simulated camera-sensor example:

- A Habitat-Sim scene rendered on the GPU.
- A grey floor and several colored blocks.
- A Franka Panda arm loaded from a URDF with real visual meshes.
- A fixed `wrist_camera_link` attached to the Panda hand.
- Joint motion that changes the wrist camera viewpoint.
- RGB and depth observations read from Habitat-Sim.
- External OpenCV preview windows that make the sensor streams visible while the
  simulator runs.

The external preview is the feedback loop in this chapter: instead of trusting
that the simulator produced valid arrays, you can inspect the RGB and depth
streams directly as the arm moves.

The overview clip shows the simulated scene, the colored blocks, and the moving
articulated arm from an external viewpoint.

<video controls muted loop>
  <source src="../assets/habitat-camera-sensors/habitat_overview.mp4" type="video/mp4">
</video>

The paired stream shows the wrist RGB camera and the wrist depth camera changing
as the arm moves.

<video controls muted loop>
  <source src="../assets/habitat-camera-sensors/external_rgb_depth_side_by_side.mp4" type="video/mp4">
</video>

## Ask Codex to Build the Camera Sensor Example

Start Codex CLI from the tutorial root and give it a prompt like this:

```text
I want to create a Habitat-Sim camera sensor example for a Dora tutorial.

Please use current official Habitat-Sim installation guidance before choosing
commands. Use an isolated local environment. Do not expose secrets, private
hostnames, tokens, or absolute home paths in committed files or tutorial text.

Target:
- Install Habitat-Sim with GPU rendering enabled on this Ubuntu desktop machine.
- Create a small simulated scene with a floor and several colored blocks.
- Use a real Franka Panda URDF with visual meshes.
- Add a fixed camera link to the Panda hand.
- Move the Panda joints so the wrist camera viewpoint changes over time.
- Read both RGB and depth observations from the wrist camera.
- Show the RGB and depth streams in external OpenCV windows when a desktop
  display is available.
- Support a headless mode that still runs the simulation and writes local
  verification outputs.

Please create a run script that:
1. Creates or reuses an isolated Habitat-Sim environment.
2. Installs pinned dependencies.
3. Prints OS, Python, Habitat-Sim, OpenCV, NumPy, Trimesh, display, and GPU
   information.
4. Runs the simulated scene.
5. Fails if the RGB, depth, and overview outputs were not generated.

After running it, document any pitfalls and keep the example self-contained.
```

The important details in the prompt are:

- Ask the assistant to verify Habitat-Sim installation details before writing
  commands.
- Treat Habitat-Sim as the sensor source, not as a replacement for Dora or
  Rerun.
- Keep the arm, scene, and generated outputs inside one verification example.
- Include a no-window mode so the example can still run over SSH or in CI-like
  environments.

## Project Layout

A typical local workspace that Codex creates for this exercise looks like this:

```text
verification/habitat-camera-sensors/
├── assets/
│   ├── franka_description/
│   │   ├── LICENSE
│   │   ├── SOURCE.txt
│   │   └── meshes/
│   └── franka_panda_with_wrist_camera.urdf
├── camera_sensor_scene.py
├── environment.yml
├── README.md
└── run.sh
```

Generated runtime files stay out of the tutorial source:

- `.tools/` contains the local micromamba binary.
- `.mamba-root/` contains the local Conda environment.
- `assets/habitat_wrist_camera_probe.glb` is generated from the script.
- `outputs/` contains generated local verification media and notes.

Only curated book media files are copied into the language-specific
`src/assets/` directories, following the same asset layout used by the earlier
chapters.

## Install and Smoke Test

On a Linux desktop or SSH session with access to the desktop display:

```bash
cd verification/habitat-camera-sensors
DISPLAY=:1 ./run.sh
```

If no display is available, run without OpenCV preview windows:

```bash
cd verification/habitat-camera-sensors
SHOW_WINDOWS=0 ./run.sh
```

Expected success markers include:

```text
Verified: Habitat-Sim overview output was generated.
Verified: wrist RGB output was generated.
Verified: wrist depth output was generated.
```

The script also writes `outputs/environment.txt`, which should include the
Habitat-Sim, OpenCV, NumPy, Trimesh, display, and GPU versions used for the run.

## Scene and Panda Model

The scene is intentionally minimal. A grey floor and four small colored boxes
are enough to check color rendering, camera direction, and depth values without
adding unrelated simulator complexity.

Habitat-Sim uses a Y-up world for this example. The helper code keeps the cube
positions in Habitat coordinates, then converts them to the Z-up source
coordinates used when Trimesh exports the GLB scene.

```python
def habitat_to_scene_point(point: np.ndarray) -> tuple[float, float, float]:
    return (float(point[0]), float(-point[2]), float(point[1]))

floor = make_box((80.0, 80.0, 0.04), (0.0, 0.0, -0.02), (120, 120, 120, 255))
centers = cube_centers_for_camera(position, forward, right)
for center, color, size in zip(centers, colors, sizes):
    cubes.append(make_box(size, habitat_to_scene_point(center), color))
```

The arm model is a Franka Panda URDF. The mesh files come from the Franka ROS
`franka_description` package, and the verification example keeps the copied
license and source note under `assets/franka_description/`.

The URDF includes seven revolute Panda joints:

- `panda_joint1`
- `panda_joint2`
- `panda_joint3`
- `panda_joint4`
- `panda_joint5`
- `panda_joint6`
- `panda_joint7`

Habitat-Sim loads it as an articulated object:

```python
manager = sim.get_articulated_object_manager()
arm = manager.add_articulated_object_from_urdf(str(urdf_path), fixed_base=True)
arm.motion_type = MotionType.KINEMATIC
arm.transformation = mn.Matrix4.rotation_x(mn.Rad(-math.pi / 2.0))
```

The root rotation maps the Panda URDF's Z-up model frame into the Habitat Y-up
world, so the arm stands on the floor instead of lying across it.

The animation changes `arm.joint_positions` each frame:

```python
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
```

The RGB stream is useful for checking color, object visibility, and whether the
camera pose follows the wrist motion.

<video controls muted loop>
  <source src="../assets/habitat-camera-sensors/external_rgb_stream.mp4" type="video/mp4">
</video>

## RGB and Depth Sensors

The simulator uses two pinhole camera sensors on the agent: one color sensor and
one depth sensor.

```python
def sensor_spec(uuid: str, sensor_type: SensorType) -> CameraSensorSpec:
    spec = CameraSensorSpec()
    spec.uuid = uuid
    spec.sensor_type = sensor_type
    spec.sensor_subtype = SensorSubType.PINHOLE
    spec.resolution = [HEIGHT, WIDTH]
    spec.position = [0.0, 0.0, 0.0]
    spec.orientation = [0.0, 0.0, 0.0]
    return spec
```

Each frame, the script updates the agent pose from the wrist camera link and
then reads both observations:

```python
set_camera(agent, position, rotation)
observations = sim.get_sensor_observations()
rgb = observations["color"]
depth = observations["depth"]
```

The raw depth array is kept as floating-point data. For the preview window, the
script converts it into a color-mapped image:

```python
depth_clipped = np.clip(depth, 0.0, 6.0)
depth_norm = (255.0 * (1.0 - depth_clipped / 6.0)).astype(np.uint8)
depth_color = cv2.applyColorMap(depth_norm, cv2.COLORMAP_TURBO)
```

The depth stream gives a second view of the same camera pose, with nearer
surfaces and farther surfaces mapped to different colors for inspection.

<video controls muted loop>
  <source src="../assets/habitat-camera-sensors/external_depth_stream.mp4" type="video/mp4">
</video>

## Bind the Camera to the Wrist Transform

The URDF includes a fixed `wrist_camera_mount` joint and a `wrist_camera_link`.
The mount uses a small yaw offset and a forward/down pitch offset, so the optical
axis looks toward the blocks instead of pointing almost straight into the floor.
The verification script also checks that the camera trajectory stays above the
floor and that the optical axis does not intersect the floor too close to the
camera. The guard uses Habitat's Y coordinate as height.

The script asks Habitat-Sim for that link scene node and reads the full world
transform:

```python
link_id = arm.get_link_id_from_name("wrist_camera_link")
node = arm.get_link_scene_node(link_id)
transform = node.absolute_transformation()
position = np.array(transform.translation, dtype=np.float64)
rotation_matrix = matrix3_to_np(transform.rotation())
rotation = quaternion.from_rotation_matrix(rotation_matrix)
```

Both `position` and `rotation` are applied to the Habitat-Sim agent camera. The
camera is therefore fixed to the robot wrist: when the Panda hand translates,
tilts, or rolls, the RGB and depth streams move with that same transform.

## Visual Preview Windows

When a desktop display is available, OpenCV shows the overview, RGB, and depth
streams in separate windows:

```python
cv2.namedWindow("Wrist RGB Camera", cv2.WINDOW_NORMAL)
cv2.namedWindow("Wrist Depth Camera", cv2.WINDOW_NORMAL)
cv2.imshow("Wrist RGB Camera", wrist_bgr)
cv2.imshow("Wrist Depth Camera", wrist_depth_color)
cv2.waitKey(int(1000 / FPS))
```

The same script supports `SHOW_WINDOWS=0` through `run.sh`, which keeps the
simulation path usable when no desktop display is attached.

## Next Step

The next step is to connect Habitat-Sim RGB and depth outputs to a Dora dataflow, then use Rerun to record or display sensor data, robot pose, and runtime status.
