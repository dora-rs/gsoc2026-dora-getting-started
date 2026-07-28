# Dora 控制 Rerun 场景运动

## 版本信息

| 组件 | 版本 / 环境 |
| --- | --- |
| 操作系统 | Ubuntu 22.04.5 LTS, x86_64 |
| Python | CPython 3.10.12 |
| Dora CLI | 0.5.0 |
| dora-rs Python 包 | `dora-rs==0.5.0` |
| Rerun CLI 与 Python SDK | 0.33.0 |
| uv | 0.11.17 |
| pyarrow | 24.0.0 |
| PyYAML | 6.0.3 |

## 下载

- [完整 Rerun 与 Dora 参考工程](../assets/week2-rerun-scene/rerun-scene-reference.zip)

这与上一章使用的是同一套固定场景、模型、轨迹和 Dora 工程。

## 目标

上一章构建了一个静态 Rerun 场景。本章保留同一个地面、正方体、圆柱体、机器人和小车，然后用 Dora 驱动运动：

- Dora 运行 `controller` 节点和 `visualizer` 节点。
- controller 持续发布场景状态。
- 机器人先启动，绕过正方体，靠近圆柱体并停下。
- 小车稍后启动，沿另一条路径绕过正方体，靠近圆柱体并停下。
- Rerun 记录持续变化的 transform，并捕获一段短 Viewer 录屏。

<video controls muted loop src="../assets/week2-rerun-scene/rerun_viewer_recording.mp4"></video>

## 检查 Dora 控制运动

继续使用上面下载的参考工程。运动实现已经包含在工程中，因此让助手解释并验证它，
不要修改场景和模型资产：

```text
检查已经提供的 Dora 控制 Rerun 参考工程。

不要替换 glTF 文件、修改物体坐标、重新设计路径或重新生成场景。解释
dataflow.yml 如何连接 controller.py 和 visualizer.py，trajectory.py 如何延迟并
依次启动两个角色，以及 run.sh 如何生成 .rrd。

先运行源码检查，再执行 `bash run.sh`。确认录制从初始位置开始、两个角色都到达最终
waypoint，并且 artifacts/dora_rerun_scene.rrd 非空。报告错误和脱敏后的版本信息，
不要输出身份、网络或密钥信息。
```

固定源码消除了场景生成差异，同时保留了有价值的助手工作流：检查 dataflow、运行、
诊断错误并验证结果。

## Dora Dataflow

这个 dataflow 有两个节点：

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

`controller` 负责运动状态，`visualizer` 负责 Rerun 录制。这个边界接近真实 robotics 系统的组织方式：一部分发布状态，另一部分观察和渲染状态。

## 轨迹

路径只在 `trajectory.py` 中定义一次。Dora 发布采样后的状态，Rerun 记录对应的模型 transform。

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

时间线前段会刻意让两个对象停在起点，给 Viewer 录屏留出启动时间。机器人先启动，小车稍后启动。这样两个对象会依次绕行，而不是同时挤到障碍物旁边。

## Controller 节点

`controller.py` 将 JSON 场景状态作为 Apache Arrow 字符串通过 Dora 发送。对于第一个 Dora 与 Rerun 示例来说，JSON 容易阅读，也方便排查。

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

在更大的项目中，你可以把这个 JSON payload 换成更结构化的 Arrow schema。本教程先使用最小形态，把数据流跑通并可视化。

## Visualizer 节点

`visualizer.py` 接收场景状态，先记录静态场景，再逐帧记录移动对象。

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

实际文件会同时更新机器人和小车的 transform，并包含 heading；正方体、圆柱体、地面和 glTF 资产保持静态。

## 运行 Dora 控制场景

运行同一个验证脚本：

```bash
cd rerun-scene-reference
bash run.sh
```

预期成功标记：

```text
visualizer received final frame
Verified: Rerun Viewer recording was generated.
Verified: Rerun recording was generated.
```

脚本会先创建保存版 `.rrd`，然后启动 live Rerun Viewer capture 并再次运行 dataflow。这样录屏会从初始场景开始，而不是直接跳到最终状态。

## 完整运动源码

下面直接展示完整文本源码。参考工程压缩包中还包含 glTF 文件和 Viewer 录制脚本。

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

## 桌面捕获注意事项

SSH shell 不一定继承当前桌面 display。脚本会依次尝试当前 `DISPLAY`、`:1` 和 `:0`。
如果 Viewer 没有打开，应把 `DISPLAY` 明确设置为当前桌面会话，然后重新执行捕获。

如果没有桌面 display，Rerun 可能会输出：

```text
neither WAYLAND_DISPLAY nor WAYLAND_SOCKET nor DISPLAY is set
```

这在 headless 主机上是正常现象。可以之后在有桌面的机器上打开生成的 `.rrd`，或者在环境允许时使用虚拟 display。

## 下一步

下一章会从 Rerun 可视化切换到 Habitat-Sim 仿真，构建一个能产生 RGB 和 depth 数据的 wrist camera 示例。
