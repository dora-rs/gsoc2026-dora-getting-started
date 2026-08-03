#!/usr/bin/env bash
source /opt/ros/humble/setup.bash
set -euo pipefail

cd /workspace
exec webots \
  --stdout \
  --stderr \
  --mode=realtime \
  /workspace/worlds/youbot_switch_office.wbt
