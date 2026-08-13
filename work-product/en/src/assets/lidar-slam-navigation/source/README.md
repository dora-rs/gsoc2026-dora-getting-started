# LiDAR, SLAM, and Navigation Reference Project

This project contains the validated Webots R2025a, ROS 2 Humble, SLAM Toolbox,
Nav2, and Dora 1.0.0-rc.4 workflow used by the tutorial.

Dora nodes run on Python 3.11.14. ROS 2 Humble subscribers and the Nav2 action
client run on system Python 3.10 workers connected through JSONL.

The supplied `worlds/default.wbt` is the official TIAGo office world from
`webots_ros2` tag `2025.0.0`. The installed `webots_ros2_tiago` package supplies
its matching robot PROTO and launch configuration.

## Reproduce

Read `VERSIONS.md`, `TUTORIAL_CONTRACT.md`, and `ASSET_GUIDE.md`, then use the
single supported entry:

```bash
bash tutorial.sh run
```

The entry builds the pinned container image when it is missing, owns the
Webots/ROS/Dora lifecycle, saves the map, waits for Nav2 to become active, and
verifies the structured mission result. The component launch scripts remain in
the project so the implementation can be inspected; they are not alternative
reproduction entries.

Official source:

- [TIAGo office world at `webots_ros2` 2025.0.0](https://github.com/cyberbotics/webots_ros2/tree/2025.0.0/webots_ros2_tiago/worlds)
- [TIAGo Lite model at Webots R2025a](https://github.com/cyberbotics/webots/tree/R2025a/projects/robots/pal_robotics/tiago_lite)
