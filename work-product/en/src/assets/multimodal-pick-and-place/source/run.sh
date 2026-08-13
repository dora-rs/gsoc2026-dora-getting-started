#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

TOOLS="$ROOT/.tools"
MAMBA_ROOT_PREFIX="$ROOT/.mamba-root"
MICROMAMBA="$TOOLS/bin/micromamba"
SIM_ENV="multimodal-simulation"
DORA_ENV="multimodal-dora"
DORA_CLI="$TOOLS/dora"
DORA_VERSION="1.0.0-rc.4"
DORA_ARCHIVE_SHA256="251cb47b6e306049082c9d5fc30aa6e73c7be1ad27acfbcfff2f23be3202dd5a"

mkdir -p "$TOOLS" outputs/logs
if [[ ! -x "$MICROMAMBA" ]]; then
  curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest |
    tar -xj -C "$TOOLS" bin/micromamba
fi

export MAMBA_ROOT_PREFIX
if [[ ! -x "$MAMBA_ROOT_PREFIX/envs/$SIM_ENV/bin/python" ]]; then
  "$MICROMAMBA" create -y -n "$SIM_ENV" -f environment.yml
fi
if [[ ! -x "$MAMBA_ROOT_PREFIX/envs/$DORA_ENV/bin/python" ]]; then
  "$MICROMAMBA" create -y -n "$DORA_ENV" -f environment-dora.yml
fi

if [[ ! -x "$DORA_CLI" ]]; then
  archive="$TOOLS/dora-cli.tar.gz"
  curl -fsSL \
    "https://github.com/dora-rs/dora/releases/download/v$DORA_VERSION/dora-cli-x86_64-unknown-linux-gnu.tar.gz" \
    -o "$archive"
  echo "$DORA_ARCHIVE_SHA256  $archive" | sha256sum --check --status
  tar -xzf "$archive" -C "$TOOLS"
  install -m 0755 "$TOOLS/dora-cli-x86_64-unknown-linux-gnu/dora" "$DORA_CLI"
fi

SIM_PYTHON="$MAMBA_ROOT_PREFIX/envs/$SIM_ENV/bin/python"
DORA_BIN="$MAMBA_ROOT_PREFIX/envs/$DORA_ENV/bin"
export MULTIMODAL_SIM_PYTHON="$SIM_PYTHON"
export MULTIMODAL_TRAJECTORY="${MULTIMODAL_TRAJECTORY:-$ROOT/validated-trajectory.json}"
export MULTIMODAL_OUTPUT="${MULTIMODAL_OUTPUT:-$ROOT/outputs/dora-run}"
export OLLAMA_MODEL="${OLLAMA_MODEL:-qwen3-vl:8b-instruct}"
export OLLAMA_URL="${OLLAMA_URL:-http://127.0.0.1:11434}"
runtime_path="$TOOLS:$DORA_BIN"
IFS=':' read -r -a path_entries <<< "$PATH"
for entry in "${path_entries[@]}"; do
  [[ -z "$entry" || "$entry" == "$TOOLS" || "$entry" == "$DORA_BIN" ]] && continue
  [[ -x "$entry/uv" ]] && continue
  runtime_path="$runtime_path:$entry"
done
export PATH="$runtime_path"

echo "== Verifying isolated runtimes =="
"$SIM_PYTHON" -c 'import habitat_sim; print("Habitat-Sim runtime ready")'
"$DORA_BIN/python" -c 'import importlib.metadata as m; print("dora-rs", m.version("dora-rs"))'
"$DORA_CLI" --version

echo "== Running focused tests =="
"$SIM_PYTHON" -m unittest discover -s tests

if [[ "${SIMULATION_ONLY:-0}" == "1" ]]; then
  "$SIM_PYTHON" prepare_trajectory.py --output outputs/trajectory
  "$SIM_PYTHON" record_demo.py \
    --trajectory outputs/trajectory/trajectory.json \
    --output outputs/demo
  exit 0
fi

curl -fsS "$OLLAMA_URL/api/tags" >/dev/null
echo "== Running the complete Dora application =="
"$DORA_BIN/python" -c 'import dora; dora.run("dataflow.yml")' \
  2>&1 | tee outputs/logs/dora-run.log
grep -q "TASK_SUCCESS" outputs/logs/dora-run.log
echo "Verified: complete Dora vision-gated task succeeded."
