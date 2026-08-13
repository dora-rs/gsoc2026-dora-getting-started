#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE="${NAVIGATION_IMAGE:-dora-lidar-navigation:final-package}"
NAME="${NAVIGATION_CONTAINER:-book-reader-lidar-navigation}"
DISPLAY_VALUE="${DISPLAY:-:1}"
EXPLORE_SECONDS=45
TIMEOUT_SECONDS=480
SYSTEM_PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
DORA_PATH="/opt/dora-venv/bin:${SYSTEM_PATH}"
usage(){ printf '%s\n' 'Usage: ./tutorial.sh <preflight|run|verify|clean> [--explore-seconds N] [--timeout-seconds N]'; }
log(){ printf '[tutorial] %s\n' "$*"; }
ros_exec(){ docker exec "$NAME" env PATH="$SYSTEM_PATH" bash -lc "source /opt/ros/humble/setup.bash; $*"; }
dora_exec(){ docker exec "$NAME" env PATH="$DORA_PATH" bash -lc "source /opt/ros/humble/setup.bash; $*"; }
remove_container(){ docker rm -f "$NAME" >/dev/null 2>&1 || true; }
ensure_image(){
  if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
    log "building missing image=$IMAGE"
    docker build --tag "$IMAGE" "$ROOT"
  fi
}
clean_generated(){
  remove_container
  docker run --rm -v "$ROOT:/workspace" "$IMAGE" bash -lc \
    'rm -rf /workspace/outputs /workspace/logs; mkdir -p /workspace/outputs /workspace/logs; chmod 0777 /workspace/outputs /workspace/logs'
}
preflight(){
  command -v docker >/dev/null
  docker info >/dev/null
  ensure_image
  DISPLAY="$DISPLAY_VALUE" xhost >/dev/null
  log "image=$IMAGE"
  log "Dora=1.0.0-rc.4 dora-rs=1.0.0rc4 ROS=Humble Webots=R2025a"
}
start_container(){
  DISPLAY="$DISPLAY_VALUE" xhost +SI:localuser:root >/dev/null
  docker run -d --name "$NAME" --network host --gpus all --ipc host \
    -e DISPLAY="$DISPLAY_VALUE" -e QT_X11_NO_MITSHM=1 -e NVIDIA_DRIVER_CAPABILITIES=all \
    -v /tmp/.X11-unix:/tmp/.X11-unix:rw -v "$ROOT:/workspace" -w /workspace \
    "$IMAGE" sleep infinity >/dev/null
}
wait_ros(){
  local kind="$1" target="$2" limit="$3" elapsed=0
  while ((elapsed<limit)); do
    ros_exec "ros2 $kind list 2>/dev/null" | grep -Fxq "$target" && return 0
    sleep 3; elapsed=$((elapsed+3))
  done
  log "timeout: ROS $kind $target"; return 1
}
wait_lifecycle_active(){
  local node="$1" limit="$2" elapsed=0
  while ((elapsed<limit)); do
    if ros_exec "ros2 lifecycle get '$node' 2>/dev/null" | grep -Eq '^active([[:space:]]|$)'; then
      return 0
    fi
    sleep 2; elapsed=$((elapsed+2))
  done
  log "timeout: lifecycle node $node did not become active"; return 1
}
wait_result(){
  local elapsed=0
  while ((elapsed<TIMEOUT_SECONDS)); do
    [[ -f "$ROOT/outputs/mission-result.json" ]] && return 0
    sleep 5; elapsed=$((elapsed+5))
  done
  log 'timeout: mission result'; return 1
}
verify(){
  python3 - "$ROOT" <<'PY'
import json, sys
from pathlib import Path
r=Path(sys.argv[1]); x=json.loads((r/'outputs/mission-result.json').read_text())
assert x['state']=='SUCCEEDED' and x['goal_sent'] and x['goal_accepted'], x
assert all(x['sensors'][k]>0 for k in ('scan_samples','odom_samples','known_cells')), x
for n in ('office.pgm','office.yaml'):
 p=r/'outputs/map'/n; assert p.is_file() and p.stat().st_size>0, p
print('VERIFIED: SLAM map generated and Dora/Nav2 navigation succeeded')
PY
}
run(){
  preflight; clean_generated; start_container; trap remove_container EXIT INT TERM
  { dora_exec 'dora --version; python --version; python -c "import importlib.metadata; print(importlib.metadata.version(\"dora-rs\"))"'; ros_exec '/usr/bin/python3 --version'; } >"$ROOT/logs/versions.log" 2>&1
  log 'starting Webots, TIAgO, RViz, and SLAM Toolbox'
  docker exec -d "$NAME" env PATH="$SYSTEM_PATH" bash -lc 'source /opt/ros/humble/setup.bash; cd /workspace; bash launch-baseline.sh >logs/baseline.log 2>&1'
  wait_ros topic /scan 180; wait_ros topic /map 180
  log "exploring for ${EXPLORE_SECONDS}s and saving the map"
  ros_exec "cd /workspace; /usr/bin/python3 explore_with_lidar.py '$EXPLORE_SECONDS'; mkdir -p outputs/map; ros2 run nav2_map_server map_saver_cli -f outputs/map/office" | tee "$ROOT/logs/mapping.log"
  log 'starting Nav2 and focused tests'
  docker exec -d "$NAME" env PATH="$SYSTEM_PATH" bash -lc 'source /opt/ros/humble/setup.bash; cd /workspace; bash launch-nav2-live.sh'
  ros_exec 'cd /workspace/dora; /usr/bin/python3 -m pytest -q' | tee "$ROOT/logs/tests.log"
  wait_ros action /navigate_to_pose 180
  wait_lifecycle_active /bt_navigator 180
  log 'Nav2 is active; starting Dora dataflow'
  docker exec -d "$NAME" env PATH="$DORA_PATH" bash -lc 'source /opt/ros/humble/setup.bash; cd /workspace/dora; dora run dataflow.yml >../logs/dora.log 2>&1'
  wait_result; verify | tee "$ROOT/logs/verification.log"
  ros_exec 'chmod -R a+rX /workspace/outputs /workspace/logs' >/dev/null
  log PASS
}
cmd="${1:-}"; shift || true
while (($#)); do case "$1" in --explore-seconds) EXPLORE_SECONDS="$2"; shift 2;; --timeout-seconds) TIMEOUT_SECONDS="$2"; shift 2;; -h|--help) usage; exit 0;; *) usage; exit 2;; esac; done
case "$cmd" in preflight) preflight;; run) run;; verify) verify;; clean) clean_generated;; -h|--help) usage;; *) usage; exit 2;; esac
