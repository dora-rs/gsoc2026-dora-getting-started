#!/usr/bin/env bash
source /opt/ros/humble/setup.bash
set -euo pipefail

cd /workspace
exec webots \
  --batch \
  --stdout \
  --stderr \
  --mode=realtime \
  /workspace/worlds/week11_process_supervision.wbt
