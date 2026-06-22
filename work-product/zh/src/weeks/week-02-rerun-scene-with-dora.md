# Rerun 介绍与静态场景

## 版本信息

本章在一台 Linux 桌面环境中通过 SSH 完成验证。

- 操作系统：Ubuntu 22.04.5 LTS, x86_64
- Python：CPython 3.10.12
- Rerun CLI 与 Python SDK：0.33.0
- 验证示例：`verification/week2-rerun-scene`

## Rerun 是什么

Rerun 是面向 robotics、computer vision 和 physical AI 系统的可视化与日志工具。程序可以记录 transform、box、image、point、text、tensor、时间序列状态等带类型的数据。Rerun Viewer 可以实时查看这些数据，也可以打开保存下来的 `.rrd` 录制文件。

官方 Python SDK 包名是 `rerun-sdk`，Python import 名称是 `rerun`。安装 Python
SDK 后也会得到 Viewer 的命令行工具。

编写本章时，`rerun-sdk==0.33.0` 要求 Python 3.10 或更新版本。本章检查到的 PyPI wheel 包括 Windows x86-64、Linux x86-64、Linux ARM64 和 macOS ARM64。如果你的平台没有对应 wheel，请以 Rerun 官方安装和 troubleshooting 文档为准。

## 目标

本章创建后续章节会继续使用的静态场景基础：

- 一个地面平面。
- 一个正方体障碍物。
- 一个圆柱体目标。
- 一个可复用的人型机器人 glTF 模型。
- 一个可复用的小车 glTF 模型。
- 一张真实 Rerun Viewer 截图，用来确认场景可以被可视化检查。

本章中机器人和小车不会移动。先把第一个 Rerun 示例保持为静态，可以更容易理解坐标系、场景层级、资产和 Viewer 工作流，然后再加入 Dora 控制的运动。

![Rerun Viewer 静态场景截图](../assets/week2-rerun-scene/rerun_viewer_screenshot.png)

## 让 Codex 准备静态场景

在教程根目录启动 Codex CLI，然后给它类似下面的 prompt：

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

这个 prompt 中最重要的点是：

- 要求助手先检查官方文档，再决定包名和 API。
- 使用固定版本的、可复现的 Python 环境。
- 使用真实 Rerun Viewer 输出，而不是手绘示意图。
- 使用可复用 3D 资产，而不是只用一次性的 primitive 占位。

## 工程结构

验证示例位于：

```text
verification/week2-rerun-scene/
├── generate_models.py
├── models/
├── requirements.txt
├── run.sh
└── visualizer.py
```

下一章会继续扩展同一个验证目录，加入 Dora 节点和运动捕获。运行时生成的文件不作为教程源码维护：

- `.venv/` 保存本地 Python 环境。
- `models/` 保存可复用的人型机器人和小车 glTF 模型。
- `artifacts/` 保存生成的 `.rrd` 文件和本地 Viewer 媒体。
- `logs/` 保存运行日志。
- `out/` 保存 Dora 运行会话数据。

经过整理的 Rerun Viewer 媒体会复制到 `src/assets/`，这样 book 可以直接渲染它们。

## 依赖

静态 Rerun 部分使用：

```text
rerun-sdk==0.33.0
```

教程中固定版本是有意义的，因为它让问题更容易复现。当你主动升级依赖时，也要更新本章开头的版本信息，并重新运行验证脚本。

## 记录静态对象

Rerun 场景从世界坐标系和几个静态对象开始。静态数据只需要记录一次，后续录制中会持续复用。

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

完整的 `visualizer.py` 还会记录地面、机器人模型和小车模型，并放在清晰的层级下：

```text
world/
├── floor
├── obstacles/cube
├── goal/cylinder
└── actors/
    ├── robot
    └── car
```

## 添加可复用 glTF 资产

机器人和小车以 glTF 资产的形式记录：

```python
from pathlib import Path

import rerun as rr

MODELS = Path("models")

rr.log("world/actors/robot", rr.Asset3D(path=MODELS / "humanoid_robot.gltf"), static=True)
rr.log("world/actors/car", rr.Asset3D(path=MODELS / "small_car.gltf"), static=True)
```

在本教程中，glTF 比 OBJ/MTL 更合适。OBJ 虽然容易生成，但在这个环境里 Rerun Viewer 会渲染成白模；glTF 内置材质更稳定。

## 运行静态场景

在 Linux 或有桌面会话的 SSH 机器上运行：

```bash
cd verification/week2-rerun-scene
./run.sh
```

脚本会创建 `.venv`、安装依赖、生成 glTF 模型、保存 `.rrd`，并打印验证时的软件版本。

预期成功标记包括：

```text
Verified: Rerun recording was generated.
```

如果没有桌面 display，可以保留生成的 `.rrd`，之后在有桌面的机器上打开：

```bash
cd verification/week2-rerun-scene
source .venv/bin/activate
rerun artifacts/dora_rerun_scene.rrd
```

## 下一步

下一章会保持这个场景布局，并使用 Dora 发布不断变化的机器人和小车 transform。这样静态 Rerun 场景就会变成一个小型 Dora 控制运动示例。
