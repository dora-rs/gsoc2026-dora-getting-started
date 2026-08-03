#!/usr/bin/env bash
set -euo pipefail

IMAGE="${WEEK11_IMAGE:-octos-process-supervision:humble}"
NAME="${WEEK11_CONTAINER:-octos-process-supervision}"
DISPLAY_VALUE="${DISPLAY:-:1}"
WORKSPACE="${WEEK11_WORKSPACE:-${PWD}}"
DORA_CLI="${DORA_CLI:-${HOME}/.cargo/bin/dora}"

mkdir -p "${WORKSPACE}"
xhost +SI:localuser:root >/dev/null

if [[ ! -x "${DORA_CLI}" ]]; then
  echo "Dora CLI not found at ${DORA_CLI}" >&2
  exit 1
fi

docker rm -f "${NAME}" >/dev/null 2>&1 || true
docker run --rm -it \
  --name "${NAME}" \
  --network host \
  --gpus all \
  --ipc host \
  --env DISPLAY="${DISPLAY_VALUE}" \
  --env QT_X11_NO_MITSHM=1 \
  --env NVIDIA_DRIVER_CAPABILITIES=all \
  --env __NV_PRIME_RENDER_OFFLOAD=1 \
  --env __GLX_VENDOR_LIBRARY_NAME=nvidia \
  --env OLLAMA_URL="${OLLAMA_URL:-http://127.0.0.1:11434}" \
  --env OLLAMA_OPENAI_BASE_URL="${OLLAMA_OPENAI_BASE_URL:-http://127.0.0.1:11434/v1}" \
  --env OLLAMA_MODEL="${OLLAMA_MODEL:-qwen3-vl:8b-instruct}" \
  --env WEEK11_INITIAL_TEMPERATURE_C="${WEEK11_INITIAL_TEMPERATURE_C:-32.0}" \
  --env WEEK11_INITIAL_PRESSURE_KPA="${WEEK11_INITIAL_PRESSURE_KPA:-162.0}" \
  --env WEEK11_HEATING_RATE_C_PER_S="${WEEK11_HEATING_RATE_C_PER_S:-0.25}" \
  --env WEEK11_PRESSURE_RATE_KPA_PER_S="${WEEK11_PRESSURE_RATE_KPA_PER_S:-0.32}" \
  --env WEEK11_COOLING_EFFECT_C_PER_S="${WEEK11_COOLING_EFFECT_C_PER_S:--1.35}" \
  --env WEEK11_RELIEF_EFFECT_KPA_PER_S="${WEEK11_RELIEF_EFFECT_KPA_PER_S:--3.50}" \
  --volume /tmp/.X11-unix:/tmp/.X11-unix:rw \
  --volume "${DORA_CLI}:/usr/local/bin/dora:ro" \
  --volume "${WORKSPACE}:/workspace" \
  --workdir /workspace \
  "${IMAGE}" \
  bash
