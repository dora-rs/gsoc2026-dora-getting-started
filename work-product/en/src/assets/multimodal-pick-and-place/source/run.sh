#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

TOOLS="$ROOT/.tools"
MAMBA_ROOT_PREFIX="$ROOT/.mamba-root"
MICROMAMBA="$TOOLS/bin/micromamba"
ENV_NAME="${ENV_NAME:-multimodal-pick-and-place}"

mkdir -p "$TOOLS" outputs/logs

if [[ ! -x "$MICROMAMBA" ]]; then
  echo "== Installing micromamba locally =="
  curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest |
    tar -xj -C "$TOOLS" bin/micromamba
fi

export MAMBA_ROOT_PREFIX

if [[ ! -x "$MAMBA_ROOT_PREFIX/envs/$ENV_NAME/bin/python" ]]; then
  echo "== Creating the isolated simulation environment =="
  "$MICROMAMBA" create -y -n "$ENV_NAME" -f environment.yml
else
  echo "== Reusing the isolated simulation environment =="
fi

ENV_BIN="$MAMBA_ROOT_PREFIX/envs/$ENV_NAME/bin"
export PATH="$ENV_BIN:$PATH"

echo "== Running focused tests =="
python -m unittest discover -s tests

if [[ "${SIMULATION_ONLY:-0}" == "1" ]]; then
  echo "== Running simulator-only verification =="
  python prepare_trajectory.py --output outputs/trajectory
  python record_demo.py \
    --trajectory outputs/trajectory/trajectory.json \
    --output outputs/demo
  exit 0
fi

export OLLAMA_MODEL="${OLLAMA_MODEL:-qwen3-vl:8b-instruct}"
export OLLAMA_URL="${OLLAMA_URL:-http://127.0.0.1:11434}"
export WEEK7_TRAJECTORY="${WEEK7_TRAJECTORY:-$ROOT/validated-trajectory.json}"
export WEEK7_OUTPUT="${WEEK7_OUTPUT:-$ROOT/outputs/dora-run}"

echo "== Checking the local vision service =="
curl -fsS "$OLLAMA_URL/api/tags" >/dev/null

echo "== Running the complete Dora application =="
set -o pipefail
python -c 'import dora; dora.run("dataflow.yml")' \
  2>&1 | tee outputs/logs/dora-run.log
grep -q "TASK_SUCCESS" outputs/logs/dora-run.log
echo "Verified: complete Dora vision-gated task succeeded."
