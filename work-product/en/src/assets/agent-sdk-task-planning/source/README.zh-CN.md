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

## 复现

```bash
ollama pull qwen3-vl:8b-instruct
bash tutorial.sh run
```

运行前阅读 `VERSIONS.md`、`TUTORIAL_CONTRACT.md` 和 `ASSET_GUIDE.md`。镜像不存在时，
入口会自行构建，并管理 Webots、Dora Robot API、Agents SDK 任务、验收与清理。
组件脚本只用于阅读实现，不是其他复现入口。

Agent 只能看到 `home`、`indicator_station` 和 `main_switch`。坐标保存在
`config/locations.json` 中；工具 schema 不开放任意坐标、轮速或关节角。
