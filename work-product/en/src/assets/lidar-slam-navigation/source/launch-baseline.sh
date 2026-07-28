#!/usr/bin/env bash
set -euo pipefail

mkdir -p /workspace/logs

exec ros2 launch webots_ros2_tiago robot_launch.py \
  world:=default.wbt \
  mode:=realtime \
  rviz:=true \
  slam_toolbox:=true \
  slam_cartographer:=false \
  nav:=false \
  use_sim_time:=true
