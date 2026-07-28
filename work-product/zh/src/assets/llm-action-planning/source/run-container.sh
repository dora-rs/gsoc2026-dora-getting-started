#!/usr/bin/env bash
set -euo pipefail

IMAGE="${WEEK9_IMAGE:-week9-webots-llm:humble}"
NAME="${WEEK9_CONTAINER:-week9-webots-llm}"
DISPLAY_VALUE="${DISPLAY:-:1}"
WORKSPACE="${WEEK9_WORKSPACE:-${PWD}}"
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
  --volume /tmp/.X11-unix:/tmp/.X11-unix:rw \
  --volume "${DORA_CLI}:/usr/local/bin/dora:ro" \
  --volume "${WORKSPACE}:/workspace" \
  --workdir /workspace \
  "${IMAGE}" \
  bash
