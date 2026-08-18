#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE="${ACTION_PLANNING_IMAGE:-dora-llm-action-planning:final-package}"
NAME="${ACTION_PLANNING_CONTAINER:-book-reader-llm-action}"
DISPLAY_VALUE="${DISPLAY:-:1}"
MODEL="${OLLAMA_MODEL:-qwen3-vl:8b-instruct}"
TIMEOUT_SECONDS=600
SYSTEM_PATH="/usr/local/webots:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
DORA_PATH="/opt/dora-venv/bin:${SYSTEM_PATH}"
usage(){ echo 'Usage: ./tutorial.sh <preflight|run|verify|clean> [--timeout-seconds N]'; }
log(){ printf '[tutorial] %s\n' "$*"; }
ros_exec(){ docker exec "$NAME" env PATH="$SYSTEM_PATH" bash -lc "source /opt/ros/humble/setup.bash; $*"; }
remove_container(){ docker rm -f "$NAME" >/dev/null 2>&1 || true; }
ensure_image(){ if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then log "building missing image=$IMAGE"; docker build --tag "$IMAGE" "$ROOT"; fi; }
clean_generated(){ remove_container; docker run --rm -v "$ROOT:/workspace" "$IMAGE" bash -lc 'rm -rf /workspace/outputs /workspace/logs; mkdir -p /workspace/outputs /workspace/logs; chmod 0777 /workspace/outputs /workspace/logs'; }
preflight(){
  command -v docker >/dev/null; command -v curl >/dev/null
  docker info >/dev/null; ensure_image
  curl -fsS http://127.0.0.1:11434/api/tags | grep -Fq "\"name\":\"$MODEL\""
  DISPLAY="$DISPLAY_VALUE" xhost >/dev/null
  docker run --rm --entrypoint /usr/bin/test "$IMAGE" -x /usr/local/webots/webots
  log "image=$IMAGE model=$MODEL"
  log 'Dora=1.0.0-rc.4 dora-rs=1.0.0rc4 ROS=Humble Webots=R2025a'
}
start_container(){
  DISPLAY="$DISPLAY_VALUE" xhost +SI:localuser:root >/dev/null
  docker run -d --name "$NAME" --network host --gpus all --ipc host \
    -e DISPLAY="$DISPLAY_VALUE" -e QT_X11_NO_MITSHM=1 -e NVIDIA_DRIVER_CAPABILITIES=all \
    -e OLLAMA_URL=http://127.0.0.1:11434 -e OLLAMA_MODEL="$MODEL" \
    -v /tmp/.X11-unix:/tmp/.X11-unix:rw -v "$ROOT:/workspace" -w /workspace \
    "$IMAGE" sleep infinity >/dev/null
}
wait_topic(){ local e=0; while ((e<180)); do ros_exec 'ros2 topic list 2>/dev/null' | grep -Fxq /camera/image_raw && return 0; sleep 3; e=$((e+3)); done; return 1; }
wait_result(){ local e=0; while ((e<TIMEOUT_SECONDS)); do [[ -f "$ROOT/outputs/mission-result.json" ]] && return 0; sleep 5; e=$((e+5)); done; return 1; }
verify(){
  python3 - "$ROOT" <<'PY'
import json,sys
from pathlib import Path
r=Path(sys.argv[1]); x=json.loads((r/'outputs/mission-result.json').read_text())
assert x['state']=='SUCCEEDED',x
c=x['context']; assert c['before']['state']=='on' and c['verify_off']['state']=='off',c
assert c['return_home']['status']=='succeeded',c
for n in ('observe_before.jpg','verify_off.jpg'):
 p=r/'outputs'/n; assert p.is_file() and p.stat().st_size>0,p
print('VERIFIED: LLM plan executed, switch changed on-to-off, robot returned home')
PY
}
run(){
  preflight; clean_generated; start_container; trap remove_container EXIT INT TERM
  { docker exec "$NAME" env PATH="$DORA_PATH" dora --version; ros_exec '/usr/bin/python3 --version'; } >"$ROOT/logs/versions.log" 2>&1
  log 'starting Webots scene'
  docker exec -d "$NAME" env PATH="$SYSTEM_PATH" bash -lc 'source /opt/ros/humble/setup.bash; cd /workspace; webots --batch --stdout --stderr --mode=realtime /workspace/worlds/youbot_switch_office.wbt >logs/webots.log 2>&1'
  wait_topic
  log 'running focused tests'
  ros_exec 'cd /workspace; /usr/bin/python3 -m pytest -q' | tee "$ROOT/logs/tests.log"
  log 'starting Dora LLM action-planning dataflow'
  docker exec -d "$NAME" env PATH="$DORA_PATH" bash -lc 'source /opt/ros/humble/setup.bash; cd /workspace/dora; dora run dataflow.yml >../logs/dora.log 2>&1'
  wait_result; verify | tee "$ROOT/logs/verification.log"
  ros_exec 'chmod -R a+rX /workspace/outputs /workspace/logs' >/dev/null
  log PASS
}
cmd="${1:-}"; shift || true
while (($#)); do case "$1" in --timeout-seconds) TIMEOUT_SECONDS="$2"; shift 2;; -h|--help) usage; exit 0;; *) usage; exit 2;; esac; done
case "$cmd" in preflight) preflight;; run) run;; verify) verify;; clean) clean_generated;; -h|--help) usage;; *) usage; exit 2;; esac
