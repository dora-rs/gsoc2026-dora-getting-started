#!/usr/bin/env bash
set -euo pipefail

IMAGE="${ACTION_PLANNING_IMAGE:-dora-llm-action:humble}"
NAME="${ACTION_PLANNING_CONTAINER:-dora-llm-action}"
DISPLAY_VALUE="${DISPLAY:-:1}"
WORKSPACE="${ACTION_PLANNING_WORKSPACE:-${PWD}}"

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
  --volume /tmp/.X11-unix:/tmp/.X11-unix:rw \
  --volume "${WORKSPACE}:/workspace" \
  --workdir /workspace \
  "${IMAGE}" \
  bash
