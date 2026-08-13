# 激光雷达、SLAM 与导航参考工程

本工程包含教程中经过验证的 Webots R2025a、ROS 2 Humble、SLAM Toolbox、
Nav2 与 Dora 1.0.0-rc.4 流程。

Dora nodes 使用 Python 3.11.14；ROS 2 Humble subscribers 与 Nav2 action client
使用系统 Python 3.10 workers，并通过 JSONL 连接。

`worlds/default.wbt` 来自 `webots_ros2` 的 `2025.0.0` 标签，是 TIAGo
官方办公室场景。安装的 `webots_ros2_tiago` 软件包提供与其匹配的机器人
PROTO 和启动配置。

## 复现

先阅读 `VERSIONS.md`、`TUTORIAL_CONTRACT.md` 和 `ASSET_GUIDE.md`，再使用唯一入口：

```bash
bash tutorial.sh run
```

镜像不存在时，入口会构建固定容器，并管理 Webots、ROS、Dora、地图保存、Nav2
active 等待与结构化结果验收。组件脚本保留用于阅读实现，不是其他复现入口。

官方源文件：

- [TIAGo 办公室场景，`webots_ros2` 2025.0.0](https://github.com/cyberbotics/webots_ros2/tree/2025.0.0/webots_ros2_tiago/worlds)
- [TIAGo Lite 模型，Webots R2025a](https://github.com/cyberbotics/webots/tree/R2025a/projects/robots/pal_robotics/tiago_lite)
