#!/usr/bin/env bash
set -euo pipefail

IMAGE="${AGENT_PLANNING_IMAGE:-dora-agent-sdk:humble}"
NAME="${AGENT_PLANNING_CONTAINER:-dora-agent-sdk}"
DISPLAY_VALUE="${DISPLAY:-:1}"
WORKSPACE="${AGENT_PLANNING_WORKSPACE:-${PWD}}"

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
  --volume /tmp/.X11-unix:/tmp/.X11-unix:rw \
  --volume "${WORKSPACE}:/workspace" \
  --workdir /workspace \
  "${IMAGE}" \
  bash
