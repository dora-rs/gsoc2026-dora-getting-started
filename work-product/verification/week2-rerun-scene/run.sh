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
  echo "Example root: <repo>/work-product/verification/week2-rerun-scene"
  python --version
  rerun --version
  python - <<'PY'
import rerun as rr
print("rerun-sdk", getattr(rr, "__version__", "unknown"))
PY

  echo "== Generating assets =="
  python generate_models.py

  echo "== Logging static Rerun scene =="
  python visualizer.py

  test -s artifacts/dora_rerun_scene.rrd
  echo "Verified: Rerun recording was generated."
} 2>&1 | tee logs/latest-run.log

