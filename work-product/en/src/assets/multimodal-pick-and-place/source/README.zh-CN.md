# 多模态抓取与放置参考工程

本工程包含固定的 Habitat-Sim Panda 场景、腕部 RGB 摄像机、红黄蓝方块、已验证
轨迹、Dora dataflow、本地视觉模型 client 和测试。Dora 与模型控制 nodes 使用
Python 3.11；Habitat-Sim worker 使用 Python 3.9，并通过结构化 JSONL bridge 接入。

运行脚本会创建或复用两套隔离的 micromamba 环境。先运行 focused tests 和仿真：

```bash
SIMULATION_ONLY=1 bash run.sh
```

完整 Dora 流程需要本机已运行 Ollama，并存在 `qwen3-vl:8b-instruct`：

```bash
export OLLAMA_MODEL=qwen3-vl:8b-instruct
export OLLAMA_URL=http://127.0.0.1:11434
bash run.sh
```

`outputs/` 是本地运行输出。提供的 URDF、Franka meshes、已验证轨迹、源码和测试是
固定参考输入。
