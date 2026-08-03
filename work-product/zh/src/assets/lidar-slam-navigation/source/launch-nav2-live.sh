#!/usr/bin/env bash
set -euo pipefail

PARAMS=/opt/ros/humble/share/webots_ros2_tiago/resource/nav2_params.yaml
LOG=/workspace/logs/nav2-live.log

exec ros2 launch nav2_bringup navigation_launch.py \
  use_sim_time:=true \
  autostart:=true \
  params_file:="${PARAMS}" \
  >"${LOG}" 2>&1
