# Habitat-Sim 相机传感器参考工程

本工程包含固定的 Franka Panda URDF、全部 visual meshes、场景脚本和环境定义。
`camera_sensor_scene.py` 生成灰色地面和彩色方块场景，把 RGB 与 depth camera 绑定到
Panda 腕部，并输出两路传感器画面和第三方视角。

有桌面 display 时运行：

```bash
DISPLAY=:1 bash run.sh
```

无桌面环境时运行：

```bash
SHOW_WINDOWS=0 bash run.sh
```

脚本会在当前目录创建隔离的 micromamba 环境。`outputs/`、`.tools/`、
`.mamba-root/` 和运行时生成的 GLB 都是本地输出；提供的 URDF、mesh、许可证说明和
脚本是固定参考输入。
