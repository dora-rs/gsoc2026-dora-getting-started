#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV="$ROOT/.venv"

if [[ ! -x "$VENV/bin/python" ]]; then
  "$PYTHON_BIN" -m venv "$VENV"
fi

"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/python" -m pip install -r requirements.txt

export PATH="$VENV/bin:$PATH"
export RERUN_ANALYTICS=disabled
mkdir -p artifacts logs

{
  echo "== Environment =="
  echo "Example root: <extracted-reference-directory>"
  python --version
  dora --version
  rerun --version
  python - <<'PY'
import dora
import rerun as rr
print("dora-rs python package", getattr(dora, "__version__", "unknown"))
print("rerun-sdk", getattr(rr, "__version__", "unknown"))
PY

  echo "== Running Dora dataflow =="
  if [[ "${REGENERATE_MODELS:-0}" == "1" ]]; then
    python generate_models.py
  fi
  test -s models/humanoid_robot.gltf
  test -s models/small_car.gltf
  dora run dataflow.yml --uv --stop-after 13s

  if [[ "${CAPTURE_VIEWER:-1}" == "1" ]]; then
    echo "== Rerun Viewer screenshot and recording =="
    python capture_rerun_viewer.py || true
  else
    echo "CAPTURE_VIEWER=0; skipping desktop Viewer capture."
  fi

  test -s artifacts/dora_rerun_scene.rrd
  if [[ -s artifacts/rerun_viewer_screenshot.png ]]; then
    echo "Verified: Rerun Viewer screenshot was generated."
  else
    echo "Note: Rerun Viewer screenshot was not generated."
  fi
  if [[ -s artifacts/rerun_viewer_recording.mp4 ]]; then
    echo "Verified: Rerun Viewer recording was generated."
  else
    echo "Note: Rerun Viewer recording was not generated."
  fi
  echo "Verified: Rerun recording was generated."
} 2>&1 | tee logs/latest-run.log
