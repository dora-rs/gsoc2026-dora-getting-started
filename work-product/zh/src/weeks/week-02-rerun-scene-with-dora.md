# Rerun 介绍与静态场景

## 版本信息

| 组件 | 版本 / 环境 |
| --- | --- |
| 操作系统 | Ubuntu 22.04.5 LTS, x86_64 |
| Python | CPython 3.11.14 |
| Dora CLI / Python 包 | `1.0.0-rc.4` / `dora-rs==1.0.0rc4` |
| Rerun CLI 与 Python SDK | 0.33.0 |

## 下载

- [完整 Rerun 与 Dora 参考工程](../assets/week2-rerun-scene/rerun-scene-reference.zip)
- [人型机器人 glTF 模型](../assets/week2-rerun-scene/source/models/humanoid_robot.gltf)
- [小车 glTF 模型](../assets/week2-rerun-scene/source/models/small_car.gltf)

压缩包包含本章和下一章使用的 glTF 资产、固定版本依赖、场景记录程序、Dora
节点、轨迹、录制脚本和运行脚本。

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

## 选择实现路线

<div class="prompt-route prompt-route--create">
  <span class="prompt-route__label">创造路线</span>
  <strong>创建模型与静态场景</strong>
  <p>适合探索 Rerun 场景层级与资产流水线。</p>
</div>

```text
使用 Python 3.11 创建固定到 Rerun 0.33.0 的工程。制作两个可复用 glTF 资产：
小型人形机器人和轮式小车，必须带清晰材质，不能是白模。创建静态右手 Z-up 场景，
包含地面、一个正方体障碍、一个圆柱体目标和两个模型，主体互不重叠。模型生成过程
必须确定性，并与场景记录逻辑分离。

保存非空 .rrd，打开 Rerun Viewer，只截取 Viewer 窗口，生成 960x540 截图和短 H.264
录屏。提供固定依赖、唯一运行入口、资产与场景测试和明确验收标记。实现前先给出
场景层级与坐标。
```

<div class="prompt-route prompt-route--reproduce">
  <span class="prompt-route__label">复现路线</span>
  <strong>使用已验证的 Rerun 资产</strong>
  <p>适合不把模型制作和场景搭建作为当前学习重点的读者。</p>
</div>

```text
解压提供的 Rerun 参考工程，读取 VERSIONS.md、TUTORIAL_CONTRACT.md、
ASSET_GUIDE.md 和 READER_PROMPT.md。严格保留 glTF 模型、坐标、依赖、dataflow 和
运行脚本。报告唯一入口与验收标记，只运行该入口，再检查 RRD、截图、录屏、
运行时标记和干净的 git status。不得重新生成或替换模型；缺少任何产物都报告 FAIL。
```

## Rerun 是什么

Rerun 是面向 robotics、computer vision 和 physical AI 系统的可视化与日志工具。程序可以记录 transform、box、image、point、text、tensor、时间序列状态等带类型的数据。Rerun Viewer 可以实时查看这些数据，也可以打开保存下来的 `.rrd` 录制文件。

官方 Python SDK 包名是 `rerun-sdk`，Python import 名称是 `rerun`。安装 Python
SDK 后也会得到 Viewer 的命令行工具。

`rerun-sdk==0.33.0` 要求 Python 3.10 或更新版本。这个版本提供 Windows x86-64、
Linux x86-64、Linux ARM64 和 macOS ARM64 wheels。如果你的平台没有对应 wheel，
请以 Rerun 官方安装和 troubleshooting 文档为准。

## 检查静态场景

把参考工程解压到新目录后，让编程助手检查这些固定输入，而不是重新创建：

```text
检查这个已经提供的 Rerun 与 Dora 参考工程。

把 models/humanoid_robot.gltf、models/small_car.gltf，以及
visualizer.py 中的物体坐标视为固定教程资产。不要替换、重新生成、缩放或重新排列。

总结场景层级、固定版本的 Python 包、生成输出，以及 run.sh 执行的命令。检查缺失
依赖和机器相关路径。此时不要安装、修改或运行任何内容，也不要输出用户名、主机名、
IP 地址、token 或无关系统信息。
```

这样可以让所有读者使用同一个场景，同时仍然借助编程助手理解依赖和执行流程。

## 工程结构

解压后的可运行示例结构如下：

```text
rerun-scene-reference/
├── capture_rerun_viewer.py
├── controller.py
├── dataflow.yml
├── generate_models.py
├── models/
│   ├── humanoid_robot.gltf
│   └── small_car.gltf
├── requirements.txt
├── run.sh
├── trajectory.py
└── visualizer.py
```

下一章会继续扩展同一个示例目录，加入 Dora 节点和运动捕获。运行时生成的文件不作为教程源码维护：

- `.venv/` 保存本地 Python 环境。
- `models/` 保存可复用的人型机器人和小车 glTF 模型。
- `artifacts/` 保存生成的 `.rrd` 文件和本地 Viewer 媒体。
- `logs/` 保存运行日志。
- `out/` 保存 Dora 运行会话数据。

压缩包已经包含模型资产。`generate_models.py` 仍然保留，方便检查模型的确定性构造
过程，但教程运行时以提供的 glTF 文件为固定输入。

## 依赖

静态 Rerun 部分使用：

```text
rerun-sdk==0.33.0
```

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

### 模型生成脚本源码

下面直接展示完整的确定性模型生成脚本：

```python
{{#include ../assets/week2-rerun-scene/source/generate_models.py}}
```

## 运行静态场景

在 Linux 或有桌面会话的 SSH 机器上运行：

```bash
mkdir rerun-scene-reference
unzip rerun-scene-reference.zip -d rerun-scene-reference
cd rerun-scene-reference
bash run.sh
```

脚本会创建 `.venv`、安装固定版本依赖、校验提供的 glTF 模型、保存 `.rrd`，并打印
验证时的软件版本。只有需要主动复现确定性模型生成步骤时，才设置
`REGENERATE_MODELS=1`。

预期成功标记包括：

```text
Verified: Rerun recording was generated.
```

如果没有桌面 display，可以保留生成的 `.rrd`，之后在有桌面的机器上打开：

```bash
cd rerun-scene-reference
CAPTURE_VIEWER=0 bash run.sh
source .venv/bin/activate
rerun artifacts/dora_rerun_scene.rrd
```

## 下一步

下一章会保持这个场景布局，并使用 Dora 发布不断变化的机器人和小车 transform。这样静态 Rerun 场景就会变成一个小型 Dora 控制运动示例。
