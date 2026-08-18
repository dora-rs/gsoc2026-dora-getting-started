#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV="$ROOT/.venv"
TOOLS="$ROOT/.tools"
DORA_CLI="$TOOLS/dora"
DORA_VERSION="1.0.0-rc.4"
DORA_ARCHIVE_SHA256="251cb47b6e306049082c9d5fc30aa6e73c7be1ad27acfbcfff2f23be3202dd5a"

if ! "$PYTHON_BIN" -c 'import sys; raise SystemExit(sys.version_info < (3, 11))'; then
  echo "Python 3.11 or newer is required for dora-rs 1.0.0rc4." >&2
  exit 1
fi

if [[ ! -x "$VENV/bin/python" ]]; then
  "$PYTHON_BIN" -m venv "$VENV"
fi

"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/python" -m pip install -r requirements.txt

if [[ ! -x "$DORA_CLI" ]]; then
  mkdir -p "$TOOLS"
  archive="$TOOLS/dora-cli.tar.gz"
  curl -fsSL \
    "https://github.com/dora-rs/dora/releases/download/v$DORA_VERSION/dora-cli-x86_64-unknown-linux-gnu.tar.gz" \
    -o "$archive"
  echo "$DORA_ARCHIVE_SHA256  $archive" | sha256sum --check --status
  tar -xzf "$archive" -C "$TOOLS"
  install -m 0755 "$TOOLS/dora-cli-x86_64-unknown-linux-gnu/dora" "$DORA_CLI"
fi

runtime_path="$TOOLS:$VENV/bin"
IFS=':' read -r -a path_entries <<< "$PATH"
for entry in "${path_entries[@]}"; do
  [[ -z "$entry" || "$entry" == "$TOOLS" || "$entry" == "$VENV/bin" ]] && continue
  [[ -x "$entry/uv" ]] && continue
  runtime_path="$runtime_path:$entry"
done
export PATH="$runtime_path"
export RERUN_ANALYTICS=disabled
mkdir -p artifacts logs

{
  echo "== Environment =="
  echo "Example root: <extracted-reference-directory>"
  python --version
  dora --version
  rerun --version
  python - <<'PY'
import importlib.metadata as metadata
import rerun as rr
print("dora-rs python package", metadata.version("dora-rs"))
print("rerun-sdk", getattr(rr, "__version__", "unknown"))
PY

  echo "== Running Dora dataflow =="
  if [[ "${REGENERATE_MODELS:-0}" == "1" ]]; then
    python generate_models.py
  fi
  test -s models/humanoid_robot.gltf
  test -s models/small_car.gltf
  dora run dataflow.yml --stop-after 13s

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
