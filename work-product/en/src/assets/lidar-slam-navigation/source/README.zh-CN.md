# 激光雷达、SLAM 与导航参考工程

本工程包含教程中经过验证的 Webots R2025a、ROS 2 Humble、SLAM Toolbox、
Nav2 与 Dora 0.5.0 流程。

`worlds/default.wbt` 来自 `webots_ros2` 的 `2025.0.0` 标签，是 TIAGo
官方办公室场景。安装的 `webots_ros2_tiago` 软件包提供与其匹配的机器人
PROTO 和启动配置。

## 运行

```bash
docker build -t week8-webots-nav:humble .
chmod +x run-container.sh launch-baseline.sh launch-nav2-live.sh
./run-container.sh
```

在容器中：

```bash
./launch-baseline.sh
python3 explore_with_lidar.py 75
mkdir -p maps
ros2 run nav2_map_server map_saver_cli -f maps/office
```

在另一个容器终端中启动 `launch-nav2-live.sh`，然后运行：

```bash
cd /workspace/dora
pytest -q
dora run dataflow.yml
```

官方源文件：

- [TIAGo 办公室场景，`webots_ros2` 2025.0.0](https://github.com/cyberbotics/webots_ros2/tree/2025.0.0/webots_ros2_tiago/worlds)
- [TIAGo Lite 模型，Webots R2025a](https://github.com/cyberbotics/webots/tree/R2025a/projects/robots/pal_robotics/tiago_lite)
