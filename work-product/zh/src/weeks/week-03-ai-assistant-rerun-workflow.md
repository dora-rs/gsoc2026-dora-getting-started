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

## 目标

上一章构建了一个静态 Rerun 场景。本章保留同一个地面、正方体、圆柱体、机器人和小车，然后用 Dora 驱动运动：

- Dora 运行 `controller` 节点和 `visualizer` 节点。
- controller 持续发布场景状态。
- 机器人先启动，绕过正方体，靠近圆柱体并停下。
- 小车稍后启动，沿另一条路径绕过正方体，靠近圆柱体并停下。
- Rerun 记录持续变化的 transform，并捕获一段短 Viewer 录屏。

<video controls muted loop src="../assets/week2-rerun-scene/rerun_viewer_recording.mp4"></video>

## 添加 Dora 控制运动

从上一章创建的静态场景目录开始，然后让 Codex CLI 继续扩展：

```text
I already have a static Rerun scene with a floor, cube obstacle, cylinder goal,
humanoid robot glTF model, and small car glTF model.

Please search the latest official Dora and Rerun documentation before choosing
commands or APIs. Keep the existing static scene structure and add Dora-driven
motion.

Target:
- Use dora-rs and dora-rs-cli.
- Create a Dora dataflow with a controller node and a visualizer node.
- The controller should publish scene state as JSON through Apache Arrow.
- The visualizer should receive scene state and update Rerun Transform3D values.
- The robot should start first, go around the cube, approach the cylinder, and
  stop.
- The car should start later, go around the cube on a separate lane, approach
  the cylinder, and stop.
- The Rerun Viewer recording should show the scene from the starting positions,
  not only the final state.

Please update the run script so it:
1. Creates or reuses the virtual environment.
2. Installs pinned Dora and Rerun dependencies.
3. Prints OS, Python, Dora, Rerun, and key package versions.
4. Runs the Dora dataflow.
5. Saves a .rrd recording.
6. Opens the Rerun Viewer and records only the Viewer window when a desktop
   display is available.
7. Fails if the .rrd recording was not created.

After running it, document any pitfalls and update the tutorial notes.
```

这个 prompt 会让助手保留静态场景，只增加运动层。它还强调了一个很重要的录屏细节：只录 Rerun Viewer 窗口，并且要让录屏从起点开始，而不是直接跳到最终状态。

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
cd verification/week2-rerun-scene
./run.sh
```

预期成功标记：

```text
visualizer received final frame
Verified: Rerun Viewer recording was generated.
Verified: Rerun recording was generated.
```

脚本会先创建保存版 `.rrd`，然后启动 live Rerun Viewer capture 并再次运行 dataflow。这样录屏会从初始场景开始，而不是直接跳到最终状态。

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
