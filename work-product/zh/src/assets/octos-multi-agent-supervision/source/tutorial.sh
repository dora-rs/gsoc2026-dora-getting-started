#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE="${PROCESS_IMAGE:-dora-octos-supervision:final-package}"
NAME="${PROCESS_CONTAINER:-book-reader-octos-supervision}"
DISPLAY_VALUE="${DISPLAY:-:1}"
VISION_MODEL="${VISION_MODEL:-qwen3-vl:8b-instruct}"
SUPERVISOR_MODEL="${SUPERVISOR_MODEL:-qwen2.5-coder:7b}"
RUN_SECONDS=180
SYSTEM_PATH="/usr/local/webots:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
DORA_PATH="/opt/dora-venv/bin:${SYSTEM_PATH}"
OCTOS_BIN="${OCTOS_BIN:-$(command -v octos || true)}"
OLLAMA_BIN="${OLLAMA_BIN:-$(command -v ollama || true)}"
[[ -z "$OCTOS_BIN" && -x "$HOME/.local/bin/octos" ]] && OCTOS_BIN="$HOME/.local/bin/octos"
if [[ -z "$OLLAMA_BIN" ]]; then
  OLLAMA_PID="$(pgrep -o -f '[o]llama serve' 2>/dev/null || true)"
  [[ -n "$OLLAMA_PID" ]] && OLLAMA_BIN="$(readlink -f "/proc/$OLLAMA_PID/exe")"
fi
usage(){ echo 'Usage: ./tutorial.sh <preflight|run|verify|clean> [--run-seconds N]'; }
log(){ printf '[tutorial] %s\n' "$*"; }
ros_exec(){ docker exec "$NAME" env PATH="$SYSTEM_PATH" bash -lc "source /opt/ros/humble/setup.bash; $*"; }
remove_container(){ docker rm -f "$NAME" >/dev/null 2>&1 || true; }
ensure_image(){ if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then log "building missing image=$IMAGE"; docker build --tag "$IMAGE" "$ROOT"; fi; }
clean_generated(){ remove_container; docker run --rm -v "$ROOT:/workspace" "$IMAGE" bash -lc 'rm -rf /workspace/outputs /workspace/logs /workspace/.octos; mkdir -p /workspace/outputs /workspace/logs; chmod 0777 /workspace/outputs /workspace/logs'; }
preflight(){
  command -v docker >/dev/null; command -v curl >/dev/null
  [[ -x "$OCTOS_BIN" && -x "$OLLAMA_BIN" ]]
  docker info >/dev/null; ensure_image
  docker run --rm --entrypoint /usr/bin/test "$IMAGE" -x /usr/local/webots/webots
  curl -fsS http://127.0.0.1:11434/api/tags | grep -Fq "\"name\":\"$VISION_MODEL\""
  curl -fsS http://127.0.0.1:11434/api/tags | grep -Fq "\"name\":\"$SUPERVISOR_MODEL\""
  DISPLAY="$DISPLAY_VALUE" xhost >/dev/null
  log "image=$IMAGE vision_model=$VISION_MODEL supervisor_model=$SUPERVISOR_MODEL"
  log 'Dora=1.0.0-rc.4 dora-rs=1.0.0rc4 ROS=Humble Webots=R2025a Octos=2.0.2'
}
start_container(){
  DISPLAY="$DISPLAY_VALUE" xhost +SI:localuser:root >/dev/null
  docker run -d --name "$NAME" --network host --gpus all --ipc host \
    -e DISPLAY="$DISPLAY_VALUE" -e QT_X11_NO_MITSHM=1 -e NVIDIA_DRIVER_CAPABILITIES=all \
    -e OLLAMA_URL=http://127.0.0.1:11434 -e OLLAMA_OPENAI_BASE_URL=http://127.0.0.1:11434/v1 -e OLLAMA_MODEL="$VISION_MODEL" \
    -e PROCESS_INITIAL_TEMPERATURE_C=32.0 -e PROCESS_INITIAL_PRESSURE_KPA=162.0 \
    -e PROCESS_HEATING_RATE_C_PER_S=0.25 -e PROCESS_PRESSURE_RATE_KPA_PER_S=0.32 \
    -e PROCESS_COOLING_EFFECT_C_PER_S=-1.35 -e PROCESS_RELIEF_EFFECT_KPA_PER_S=-3.50 \
    -v /tmp/.X11-unix:/tmp/.X11-unix:rw -v "$ROOT:/workspace" -w /workspace \
    "$IMAGE" sleep infinity >/dev/null
}
wait_topic(){ local e=0; while ((e<180)); do ros_exec 'ros2 topic list 2>/dev/null' | grep -Fxq /process/observer/camera/image_raw && return 0; sleep 3; e=$((e+3)); done; return 1; }
wait_api(){ local e=0; while ((e<180)); do curl -fsS http://127.0.0.1:8111/health >/dev/null 2>&1 && return 0; sleep 3; e=$((e+3)); done; return 1; }
stop_recorder(){ local pid; pid="$(cat "$ROOT/logs/recorder.pid" 2>/dev/null || true)"; [[ -n "$pid" ]] && docker exec "$NAME" kill -INT "$pid" >/dev/null 2>&1 || true; }
verify(){
  python3 - "$ROOT" <<'PY'
import json,sys
from pathlib import Path
r=Path(sys.argv[1]); run=r/'outputs/octos-runs/hardened'; rows=[json.loads(x) for x in (run/'mission-events.jsonl').read_text().splitlines()]
events=[x['event'] for x in rows]
assert all(x in events for x in ('mission_started','strategy_activated','switch_actions_completed','control_cycle_completed','mission_stopped')),events
roles={x.get('role') for x in rows if x['event']=='agent_started'}
assert {'Observer','Operator','Supervisor'} <= roles,roles
stopped=[x for x in rows if x['event']=='mission_stopped'][-1]
assert stopped['completed_cycles']>=1,stopped
assert stopped['switch_state']=={'cooling':False,'relief':False},stopped
state=json.loads((r/'outputs/final-status.json').read_text())
assert not state['process']['cooling_on'] and not state['process']['relief_open'],state
video=r/'outputs/process-supervision.mp4'; assert video.is_file() and video.stat().st_size>0,video
print('VERIFIED: Octos roles generated a strategy and completed a safe Dora control cycle')
PY
}
run(){
  preflight; clean_generated; start_container; trap 'stop_recorder; remove_container' EXIT INT TERM
  { docker exec "$NAME" env PATH="$DORA_PATH" dora --version; ros_exec '/usr/bin/python3 --version'; "$OCTOS_BIN" --version; } >"$ROOT/logs/versions.log" 2>&1
  log 'starting two-robot Webots process scene'
  docker exec -d "$NAME" env PATH="$SYSTEM_PATH" bash -lc 'source /opt/ros/humble/setup.bash; cd /workspace; webots --batch --stdout --stderr --mode=fast /workspace/worlds/process_supervision.wbt >logs/webots.log 2>&1'
  wait_topic
  log 'running focused tests'
  ros_exec 'cd /workspace; /usr/bin/python3 -m pytest -q' | tee "$ROOT/logs/tests.log"
  log 'starting Dora process dataflow'
  docker exec -d "$NAME" env PATH="$DORA_PATH" bash -lc 'source /opt/ros/humble/setup.bash; cd /workspace/dora; dora run process_dataflow.yml >../logs/dora.log 2>&1'
  wait_api
  log 'starting application-window recorder'
  docker exec -d "$NAME" env PATH="$SYSTEM_PATH" bash -lc 'source /opt/ros/humble/setup.bash; cd /workspace; /usr/bin/python3 tools/record_process_video.py --output outputs/process-supervision.mp4 --snapshots outputs/process-snapshots --fps 10 --target-engagements 2 --max-duration 500 >logs/recorder.log 2>&1 & echo $! >logs/recorder.pid; wait'
  log 'running Octos Observer, Operator, and Supervisor'
  cd "$ROOT"
  PROCESS_DORA_API=http://127.0.0.1:8111 /usr/bin/python3 tools/run_octos_multi_agent.py \
    --octos "$OCTOS_BIN" --ollama "$OLLAMA_BIN" --vision-model "$VISION_MODEL" \
    --supervisor-model "$SUPERVISOR_MODEL" --output-dir outputs/octos-runs \
    --run-name hardened --max-duration "$RUN_SECONDS" | tee "$ROOT/logs/octos-runner.log"
  curl -fsS http://127.0.0.1:8111/v1/status > "$ROOT/outputs/final-status.json"
  stop_recorder; sleep 5
  verify | tee "$ROOT/logs/verification.log"
  ros_exec 'chmod -R a+rX /workspace/outputs /workspace/logs' >/dev/null
  log PASS
}
cmd="${1:-}"; shift || true
while (($#)); do case "$1" in --run-seconds) RUN_SECONDS="$2"; shift 2;; -h|--help) usage; exit 0;; *) usage; exit 2;; esac; done
case "$cmd" in preflight) preflight;; run) run;; verify) verify;; clean) clean_generated;; -h|--help) usage;; *) usage; exit 2;; esac
