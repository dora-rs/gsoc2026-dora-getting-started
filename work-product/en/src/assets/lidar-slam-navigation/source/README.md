# LiDAR, SLAM, and Navigation Reference Project

This project contains the validated Webots R2025a, ROS 2 Humble, SLAM Toolbox,
Nav2, and Dora 1.0.0-rc.4 workflow used by the tutorial.

Dora nodes run on Python 3.11.14. ROS 2 Humble subscribers and the Nav2 action
client run on system Python 3.10 workers connected through JSONL.

The supplied `worlds/default.wbt` is the official TIAGo office world from
`webots_ros2` tag `2025.0.0`. The installed `webots_ros2_tiago` package supplies
its matching robot PROTO and launch configuration.

## Run

```bash
docker build -t dora-lidar-navigation:humble .
chmod +x run-container.sh launch-baseline.sh launch-nav2-live.sh
./run-container.sh
```

In the container:

```bash
./launch-baseline.sh
python3 explore_with_lidar.py 75
mkdir -p maps
ros2 run nav2_map_server map_saver_cli -f maps/office
```

Start `launch-nav2-live.sh` in another container shell, then run:

```bash
cd /workspace/dora
/usr/bin/python3 -m pytest -q
dora run dataflow.yml
```

Official source:

- [TIAGo office world at `webots_ros2` 2025.0.0](https://github.com/cyberbotics/webots_ros2/tree/2025.0.0/webots_ros2_tiago/worlds)
- [TIAGo Lite model at Webots R2025a](https://github.com/cyberbotics/webots/tree/R2025a/projects/robots/pal_robotics/tiago_lite)
