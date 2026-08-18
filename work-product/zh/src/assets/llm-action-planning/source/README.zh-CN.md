# LLM 动作规划参考工程

本工程包含教程中经过验证的 Webots 场景、机器人控制器、Dora dataflow、
skill 运行时、模型客户端、JSON 校验器和测试。

## 环境要求

- Ubuntu 22.04 x86_64，使用 X11 桌面
- 使用 GPU 渲染时需安装 Docker 与 NVIDIA Container Toolkit
- NVIDIA 驱动需与 Webots R2025a 容器兼容
- 容器中安装 Dora CLI 1.0.0-rc.4 与 `dora-rs==1.0.0rc4`
- Dora sidecars 使用 Python 3.11.14，ROS 2 与应用 workers 使用系统 Python 3.10
- 主机安装 Ollama 0.32.1
- 在 Ollama 中下载 `qwen3-vl:8b-instruct`

## 复现

```bash
ollama pull qwen3-vl:8b-instruct
bash tutorial.sh run
```

运行前阅读 `VERSIONS.md`、`TUTORIAL_CONTRACT.md` 和 `ASSET_GUIDE.md`。镜像不存在时，
入口会自行构建，并管理 Webots、Dora、测试、任务、视觉状态转换、返回 home 与清理。
组件脚本只用于阅读实现，不是其他复现入口。

容器使用 host 网络，因此 planner 默认通过
`http://127.0.0.1:11434` 调用 Ollama。可以按需覆盖 `OLLAMA_URL`、
`OLLAMA_MODEL` 或 `ACTION_PLANNING_OUTPUT_DIR`。

场景固定引用 Webots R2025a 官方
[youBot 模型](https://github.com/cyberbotics/webots/tree/R2025a/projects/robots/kuka/youbot)。
自定义场景和应用程序代码用于复现本教程。
