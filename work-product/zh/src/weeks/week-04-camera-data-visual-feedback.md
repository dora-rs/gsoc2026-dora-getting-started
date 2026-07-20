# 仿真场景中的相机传感器

## 版本信息

| 组件 | 版本 / 环境 |
| --- | --- |
| 操作系统 | Ubuntu 22.04.5 LTS, x86_64 |
| Python | CPython 3.9.23 |
| Habitat-Sim | 0.3.3 |
| OpenCV | 4.12.0 |
| NumPy | 1.26.4 |
| Trimesh | 4.7.4 |
| GPU | NVIDIA GeForce RTX 5090 Laptop GPU |
| NVIDIA driver | 580.159.03 |

## 目标

本章会构建一个小型 simulated camera sensor 示例：

- 一个使用 GPU 渲染的 Habitat-Sim 场景。
- 一个灰色地面和若干不同颜色的方块。
- 一个从 URDF 加载、带真实 visual meshes 的 Franka Panda 机械臂。
- 一个固定在 Panda hand 上的 `wrist_camera_link`。
- 通过 joint motion 改变 wrist camera 的视角。
- 从 Habitat-Sim 读取 RGB 和 depth observations。
- 在外部 OpenCV 窗口中实时预览传感器流。

这里的 feedback 指开发者能直接看到传感器流的反馈：不是只相信 simulator 返回了数组，而是能在机械臂运动时直接检查 RGB 和 depth 是否符合预期。

下面的概览片段展示了仿真场景、彩色方块，以及从外部视角看到的机械臂运动。

<video controls muted loop>
  <source src="../assets/habitat-camera-sensors/habitat_overview.mp4" type="video/mp4">
</video>

并排传感器流展示了机械臂运动时，wrist RGB camera 和 wrist depth camera 的同步变化。

<video controls muted loop>
  <source src="../assets/habitat-camera-sensors/external_rgb_depth_side_by_side.mp4" type="video/mp4">
</video>

## Habitat-Sim 是什么

Habitat-Sim 是 simulator。它负责创建虚拟 3D 世界，并从这个世界里渲染传感器观测，包括 RGB camera image 和 depth image。当你希望教程使用传感器数据，但又不想先搭建真实测试环境时，它提供的就是这层能力。

这和 Rerun 不一样。Rerun 是可视化与日志工具：它可以显示 robot pose、map、point cloud、image、planned path、trajectory 和 status value，但它本身不会创建物理世界，也不会主动生成 camera data。一个完整组合可以是：Habitat-Sim 生成传感器观测，Dora 在 dataflow 中传递这些观测，Rerun 负责显示或记录系统状态。

## 构建 Camera Sensor 示例

在教程根目录启动 Codex CLI，然后给它类似下面的 prompt：

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
  outputs.

Please create a run script that:
1. Creates or reuses an isolated Habitat-Sim environment.
2. Installs pinned dependencies.
3. Prints OS, Python, Habitat-Sim, OpenCV, NumPy, Trimesh, display, and GPU
   information.
4. Runs the simulated scene.
5. Fails if the RGB, depth, and overview outputs were not generated.

After running it, document any pitfalls and keep the example self-contained.
```

这个 prompt 中最重要的点是：

- 要求助手先确认 Habitat-Sim 安装细节，再写命令。
- 把 Habitat-Sim 当作 sensor source，而不是 Dora 或 Rerun 的替代品。
- 把机械臂、场景和生成结果都放在同一个可运行示例中。
- 支持无窗口模式，这样通过 SSH 或类似 CI 的环境也能跑通。

## 工程结构

Codex 为这个练习创建的典型本地 workspace 结构如下：

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

运行时生成的文件不作为教程源码维护：

- `.tools/` 保存本地 micromamba binary。
- `.mamba-root/` 保存本地 Conda environment。
- `assets/habitat_wrist_camera_probe.glb` 由脚本运行时生成。
- `outputs/` 保存本地生成的 media 和运行 notes。

只有经过整理、会被 book 直接引用的媒体会复制到各语言自己的 `src/assets/` 目录下，和前面章节保持同一套资产管理方式。

## 安装与 Smoke Test

在 Linux 桌面环境，或能访问桌面 display 的 SSH session 中运行：

```bash
cd verification/habitat-camera-sensors
DISPLAY=:1 ./run.sh
```

如果没有 display，可以关闭 OpenCV 预览窗口：

```bash
cd verification/habitat-camera-sensors
SHOW_WINDOWS=0 ./run.sh
```

预期成功标记包括：

```text
Verified: Habitat-Sim overview output was generated.
Verified: wrist RGB output was generated.
Verified: wrist depth output was generated.
```

脚本还会写入 `outputs/environment.txt`，里面包含本次运行的 Habitat-Sim、OpenCV、NumPy、Trimesh、display 和 GPU 版本信息。

## 场景与 Panda 模型

场景刻意保持最小化。一个灰色地面和四个小彩色方块已经足够检查颜色渲染、camera direction 和 depth value，不需要引入额外的 simulator 复杂度。

这个示例中，Habitat-Sim world 使用 Y-up 坐标。辅助代码会用 Habitat 坐标计算方块位置，然后转换成 Trimesh 导出 GLB 时使用的 Z-up source 坐标。

```python
def habitat_to_scene_point(point: np.ndarray) -> tuple[float, float, float]:
    return (float(point[0]), float(-point[2]), float(point[1]))

floor = make_box((80.0, 80.0, 0.04), (0.0, 0.0, -0.02), (120, 120, 120, 255))
centers = cube_centers_for_camera(position, forward, right)
for center, color, size in zip(centers, colors, sizes):
    cubes.append(make_box(size, habitat_to_scene_point(center), color))
```

机械臂模型是 Franka Panda URDF。mesh 文件来自 Franka ROS 的
`franka_description` package，这个示例会在
`assets/franka_description/` 下保留复制过来的 license 和 source note。

这个 URDF 包含七个 Panda revolute joints：

- `panda_joint1`
- `panda_joint2`
- `panda_joint3`
- `panda_joint4`
- `panda_joint5`
- `panda_joint6`
- `panda_joint7`

Habitat-Sim 会把它加载成 articulated object：

```python
manager = sim.get_articulated_object_manager()
arm = manager.add_articulated_object_from_urdf(str(urdf_path), fixed_base=True)
arm.motion_type = MotionType.KINEMATIC
arm.transformation = mn.Matrix4.rotation_x(mn.Rad(-math.pi / 2.0))
```

这个 root rotation 会把 Panda URDF 的 Z-up model frame 映射到 Habitat 的 Y-up world，所以机械臂会站在地面上，而不是横躺在地面上。

动画部分每帧更新 `arm.joint_positions`：

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

RGB stream 适合检查颜色、物体是否可见，以及 camera pose 是否跟随 wrist motion 变化。

<video controls muted loop>
  <source src="../assets/habitat-camera-sensors/external_rgb_stream.mp4" type="video/mp4">
</video>

## RGB 与 Depth 传感器

simulator 在 agent 上配置两个 pinhole camera sensors：一个 color sensor，一个 depth sensor。

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

每一帧，脚本先根据 wrist camera link 更新 agent pose，然后读取两个 observations：

```python
set_camera(agent, position, rotation)
observations = sim.get_sensor_observations()
rgb = observations["color"]
depth = observations["depth"]
```

raw depth array 会保留为 floating-point data。为了在窗口中预览，脚本会把它转换成带 colormap 的图像：

```python
depth_clipped = np.clip(depth, 0.0, 6.0)
depth_norm = (255.0 * (1.0 - depth_clipped / 6.0)).astype(np.uint8)
depth_color = cv2.applyColorMap(depth_norm, cv2.COLORMAP_TURBO)
```

Depth stream 提供同一 camera pose 下的距离反馈，近处和远处表面会被映射成不同颜色，方便检查。

<video controls muted loop>
  <source src="../assets/habitat-camera-sensors/external_depth_stream.mp4" type="video/mp4">
</video>

## 将 Camera 绑定到 Wrist Transform

URDF 中包含一个 fixed `wrist_camera_mount` joint 和一个 `wrist_camera_link`。
这个 mount 带有小的 yaw offset 和向前下方的 pitch offset，让 optical axis 朝向方块，而不是几乎垂直打向地面。
verification script 也会检查 camera trajectory 保持在地面上方，并检查 optical axis 不会在离 camera 过近的位置与地面相交。
这个 guard 使用 Habitat 的 Y coordinate 作为高度。

脚本会从 Habitat-Sim 取出这个 link 的 scene node，并读取它在 world 中的完整 transform：

```python
link_id = arm.get_link_id_from_name("wrist_camera_link")
node = arm.get_link_scene_node(link_id)
transform = node.absolute_transformation()
position = np.array(transform.translation, dtype=np.float64)
rotation_matrix = matrix3_to_np(transform.rotation())
rotation = quaternion.from_rotation_matrix(rotation_matrix)
```

`position` 和 `rotation` 都会应用到 Habitat-Sim agent camera。也就是说，
camera 真正固定在 robot wrist 上：Panda hand 平移、俯仰或滚转时，RGB 和 depth
stream 会跟随同一个 transform 变化。

## 外部预览窗口

当桌面 display 可用时，OpenCV 会分别显示 overview、RGB 和 depth stream：

```python
cv2.namedWindow("Wrist RGB Camera", cv2.WINDOW_NORMAL)
cv2.namedWindow("Wrist Depth Camera", cv2.WINDOW_NORMAL)
cv2.imshow("Wrist RGB Camera", wrist_bgr)
cv2.imshow("Wrist Depth Camera", wrist_depth_color)
cv2.waitKey(int(1000 / FPS))
```

同一个脚本也支持通过 `run.sh` 设置 `SHOW_WINDOWS=0`。这样即使没有连接桌面 display，simulation path 仍然可以运行。

## 下一步

下一步可以把 Habitat-Sim 生成的 RGB 和 depth 数据接入 Dora dataflow，并用 Rerun 记录或显示传感器数据、机器人位姿和运行状态。
