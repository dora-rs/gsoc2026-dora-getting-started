# Dora 与 Octos 连续过程监督

这个参考工程使用两台仿真移动机械臂持续监督温度和压力：

- Observer 机器人停靠传感器站，通过 Dora 读取压力，并使用 RGB 图像和本地
  多模态模型读取温度；
- Operator 机器人调用具名动作控制冷却和泄压开关；
- Supervisor 使用 Octos 和本地代码模型生成并复核受限的自适应策略。

模型选择传感器、观察时机和开关请求；Dora 传递状态与动作回执；确定性校验和
仿真安全联锁继续负责可靠执行与硬安全边界。

## 环境要求

- Ubuntu 22.04、NVIDIA GPU 和可用的 X11 桌面
- Docker Engine 与 NVIDIA Container Toolkit
- Dora CLI 1.0.0-rc.4 与 `dora-rs==1.0.0rc4`
- Dora sidecars 使用 Python 3.11.14，ROS 2 与应用 workers 使用系统 Python 3.10
- 容器提供的 Webots R2025a 与 ROS 2 Humble
- Octos 2.0.2
- Ollama 0.32.1
- `qwen3-vl:8b-instruct` 与 `qwen2.5-coder:7b`

## 复现

```bash
npm install -g @octos-org/octos@2.0.2
octos --version

ollama pull qwen3-vl:8b-instruct
ollama pull qwen2.5-coder:7b
bash tutorial.sh run
```

运行前阅读 `VERSIONS.md`、`TUTORIAL_CONTRACT.md` 和 `ASSET_GUIDE.md`。镜像不存在时，
入口会自行构建，并管理 Webots、Dora、三个 Octos 角色、录屏、验收与清理。
组件脚本只用于阅读实现，不是其他复现入口。

## 测试

在容器内运行：

```bash
cd /workspace
/usr/bin/python3 -m pytest -q
```

运行输出保存在 `outputs/`，并由 Git 忽略。
