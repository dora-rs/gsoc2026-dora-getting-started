# Rerun 场景参考工程

本工程运行一个小型 Dora dataflow，把场景状态发送到 Rerun visualizer。程序使用
`models/` 中提供的人型机器人和小车 glTF 文件，并生成
`artifacts/dora_rerun_scene.rrd`。有桌面会话时，还会捕获 Rerun Viewer 截图和短视频。

```bash
bash run.sh
```

无桌面环境时，可以只跳过 Viewer 截图和录屏，`.rrd` 仍然会生成并校验：

```bash
CAPTURE_VIEWER=0 bash run.sh
```

`generate_models.py` 保留了两个模型的确定性生成过程；需要重新生成时使用
`REGENERATE_MODELS=1 bash run.sh`。默认运行直接使用提供的 glTF 文件。`.venv/`、
`artifacts/`、`logs/` 和 `out/` 都是本地运行输出，不属于固定参考输入。
