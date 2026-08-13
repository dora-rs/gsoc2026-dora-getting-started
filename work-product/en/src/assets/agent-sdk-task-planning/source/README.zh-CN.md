# Agent SDK 自动任务规划参考工程

本工程包含教程中已经验证的 Webots 场景、三个具名位置、Dora 1.0.0-rc.4
dataflow、本地 Robot API、OpenAI Agents SDK 终端 Agent、Ollama 视觉分类器
和配套测试。

## 环境要求

- Ubuntu 22.04 x86_64，带 X11 桌面
- Docker 与 NVIDIA Container Toolkit
- 与 Webots R2025a 兼容的 NVIDIA 驱动
- 容器中安装 Dora CLI 1.0.0-rc.4 与 `dora-rs==1.0.0rc4`
- Dora sidecars 使用 Python 3.11.14，ROS 2 与应用 workers 使用系统 Python 3.10
- Ollama 与 `qwen3-vl:8b-instruct`

## 构建与运行

```bash
ollama pull qwen3-vl:8b-instruct
docker build -t dora-agent-sdk:humble .
chmod +x run-container.sh launch-webots.sh
./run-container.sh
```

在第一个容器终端启动 Webots：

```bash
./launch-webots.sh
```

在第二个终端启动 Dora dataflow：

```bash
docker exec -it dora-agent-sdk bash
cd /workspace/dora
dora run dataflow.yml
```

在第三个终端运行 Agent：

```bash
docker exec -it dora-agent-sdk bash
cd /workspace
/usr/bin/python3 agent_cli.py --task \
  "查看指示灯；如果亮着就关闭开关，确认灯灭后回到起点。"
```

Agent 只能看到 `home`、`indicator_station` 和 `main_switch`。坐标保存在
`config/locations.json` 中；工具 schema 不开放任意坐标、轮速或关节角。
