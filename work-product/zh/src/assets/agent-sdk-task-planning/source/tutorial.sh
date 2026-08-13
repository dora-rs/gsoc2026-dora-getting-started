#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE="${AGENT_PLANNING_IMAGE:-dora-agent-sdk-planning:final-package}"
NAME="${AGENT_PLANNING_CONTAINER:-book-reader-agent-planning}"
DISPLAY_VALUE="${DISPLAY:-:1}"
MODEL="${OLLAMA_MODEL:-qwen3-vl:8b-instruct}"
TASK='查看指示灯；如果亮着就关闭开关，确认灯灭后回到起点。'
TIMEOUT_SECONDS=720
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
  docker run --rm --entrypoint /usr/bin/test "$IMAGE" -x /usr/local/webots/webots
  curl -fsS http://127.0.0.1:11434/api/tags | grep -Fq "\"name\":\"$MODEL\""
  DISPLAY="$DISPLAY_VALUE" xhost >/dev/null
  log "image=$IMAGE model=$MODEL"
  log 'Dora=1.0.0-rc.4 dora-rs=1.0.0rc4 ROS=Humble Webots=R2025a Agents-SDK=0.19.0'
}
start_container(){
  DISPLAY="$DISPLAY_VALUE" xhost +SI:localuser:root >/dev/null
  docker run -d --name "$NAME" --network host --gpus all --ipc host \
    -e DISPLAY="$DISPLAY_VALUE" -e QT_X11_NO_MITSHM=1 -e NVIDIA_DRIVER_CAPABILITIES=all \
    -e OLLAMA_URL=http://127.0.0.1:11434 -e OLLAMA_OPENAI_BASE_URL=http://127.0.0.1:11434/v1 -e OLLAMA_MODEL="$MODEL" \
    -e AGENT_ARM_SETTLE_TOLERANCE=0.03 \
    -e AGENT_ARM_TASK_TIMEOUT_SIM_S=30 \
    -e AGENT_TASK_ARM_TIMEOUT_S=240 \
    -v /tmp/.X11-unix:/tmp/.X11-unix:rw -v "$ROOT:/workspace" -w /workspace \
    "$IMAGE" sleep infinity >/dev/null
}
wait_topic(){ local e=0; while ((e<180)); do ros_exec 'ros2 topic list 2>/dev/null' | grep -Fxq /camera/image_raw && return 0; sleep 3; e=$((e+3)); done; return 1; }
wait_api(){ local e=0; while ((e<180)); do curl -fsS http://127.0.0.1:8000/v1/robot/state >/dev/null 2>&1 && return 0; sleep 3; e=$((e+3)); done; return 1; }
verify(){
  python3 - "$ROOT" <<'PY'
import json,sys
from pathlib import Path
r=Path(sys.argv[1]); log=(r/'logs/agent.log').read_text()
assert '"lit": true' in log and '"lit": false' in log,log
assert '[DONE]' in log and '任务完成' in log,log
x=json.loads((r/'outputs/final-state.json').read_text())
assert x['location']=='home' and x['arm_pose']=='home',x
for n in ('indicator-before-on.jpg','indicator-after-off.jpg'):
 p=r/'outputs'/n; assert p.is_file() and p.stat().st_size>0,p
print('VERIFIED: Agents SDK used named tools, confirmed ON-to-OFF, and returned home')
PY
}
run(){
  preflight; clean_generated; start_container; trap remove_container EXIT INT TERM
  { docker exec "$NAME" env PATH="$DORA_PATH" dora --version; ros_exec '/usr/bin/python3 --version; /usr/bin/python3 -c "import importlib.metadata; print(importlib.metadata.version(\"openai-agents\"))"'; } >"$ROOT/logs/versions.log" 2>&1
  log 'starting Webots scene'
  docker exec -d "$NAME" env PATH="$SYSTEM_PATH" bash -lc 'source /opt/ros/humble/setup.bash; cd /workspace; webots --batch --stdout --stderr --mode=fast /workspace/worlds/youbot_switch_office.wbt >logs/webots.log 2>&1'
  wait_topic
  log 'running focused tests'
  ros_exec 'cd /workspace; /usr/bin/python3 -m pytest -q' | tee "$ROOT/logs/tests.log"
  log 'starting Dora Robot API dataflow'
  docker exec -d "$NAME" env PATH="$DORA_PATH" bash -lc 'source /opt/ros/humble/setup.bash; cd /workspace/dora; dora run dataflow.yml >../logs/dora.log 2>&1'
  wait_api
  log 'running Agents SDK task'
  timeout "$TIMEOUT_SECONDS" docker exec "$NAME" env PATH="$SYSTEM_PATH" bash -lc "source /opt/ros/humble/setup.bash; cd /workspace; /usr/bin/python3 agent_cli.py --task '$TASK'" | tee "$ROOT/logs/agent.log"
  curl -fsS http://127.0.0.1:8000/v1/robot/state > "$ROOT/outputs/final-state.json"
  python3 - "$ROOT" <<'PY'
import shutil,sys
from pathlib import Path
r=Path(sys.argv[1]); images=sorted((r/'outputs').glob('req-*-indicator.jpg'),key=lambda p:p.stat().st_mtime)
assert len(images)>=2,images
shutil.copyfile(images[0],r/'outputs/indicator-before-on.jpg')
shutil.copyfile(images[-1],r/'outputs/indicator-after-off.jpg')
PY
  verify | tee "$ROOT/logs/verification.log"
  ros_exec 'chmod -R a+rX /workspace/outputs /workspace/logs' >/dev/null
  log PASS
}
cmd="${1:-}"; shift || true
while (($#)); do case "$1" in --timeout-seconds) TIMEOUT_SECONDS="$2"; shift 2;; -h|--help) usage; exit 0;; *) usage; exit 2;; esac; done
case "$cmd" in preflight) preflight;; run) run;; verify) verify;; clean) clean_generated;; -h|--help) usage;; *) usage; exit 2;; esac
