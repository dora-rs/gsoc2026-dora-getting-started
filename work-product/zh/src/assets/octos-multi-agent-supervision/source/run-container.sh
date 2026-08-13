#!/usr/bin/env bash
set -euo pipefail

IMAGE="${PROCESS_IMAGE:-octos-process-supervision:humble}"
NAME="${PROCESS_CONTAINER:-octos-process-supervision}"
DISPLAY_VALUE="${DISPLAY:-:1}"
WORKSPACE="${PROCESS_WORKSPACE:-${PWD}}"

mkdir -p "${WORKSPACE}"
xhost +SI:localuser:root >/dev/null

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
  --env PROCESS_INITIAL_TEMPERATURE_C="${PROCESS_INITIAL_TEMPERATURE_C:-32.0}" \
  --env PROCESS_INITIAL_PRESSURE_KPA="${PROCESS_INITIAL_PRESSURE_KPA:-162.0}" \
  --env PROCESS_HEATING_RATE_C_PER_S="${PROCESS_HEATING_RATE_C_PER_S:-0.25}" \
  --env PROCESS_PRESSURE_RATE_KPA_PER_S="${PROCESS_PRESSURE_RATE_KPA_PER_S:-0.32}" \
  --env PROCESS_COOLING_EFFECT_C_PER_S="${PROCESS_COOLING_EFFECT_C_PER_S:--1.35}" \
  --env PROCESS_RELIEF_EFFECT_KPA_PER_S="${PROCESS_RELIEF_EFFECT_KPA_PER_S:--3.50}" \
  --volume /tmp/.X11-unix:/tmp/.X11-unix:rw \
  --volume "${WORKSPACE}:/workspace" \
  --workdir /workspace \
  "${IMAGE}" \
  bash
