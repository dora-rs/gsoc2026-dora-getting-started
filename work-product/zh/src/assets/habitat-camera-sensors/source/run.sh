#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

TOOLS="$ROOT/.tools"
MAMBA_ROOT_PREFIX="$ROOT/.mamba-root"
MICROMAMBA="$TOOLS/bin/micromamba"
ENV_NAME="habitat-camera-sensors"

mkdir -p "$TOOLS"

if [[ ! -x "$MICROMAMBA" ]]; then
  echo "== Installing micromamba locally =="
  curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xj -C "$TOOLS" bin/micromamba
fi

export MAMBA_ROOT_PREFIX

if [[ ! -x "$MAMBA_ROOT_PREFIX/envs/$ENV_NAME/bin/python" ]]; then
  echo "== Creating Habitat-Sim environment =="
  "$MICROMAMBA" create -y -n "$ENV_NAME" -f environment.yml
else
  echo "== Reusing Habitat-Sim environment =="
fi

if [[ "${SHOW_WINDOWS:-1}" == "0" ]]; then
  echo "SHOW_WINDOWS=0; running without OpenCV preview windows."
  RUN_ARGS=(--no-windows)
elif [[ -z "${DISPLAY:-}" ]]; then
  echo "DISPLAY is not set; running without OpenCV preview windows."
  RUN_ARGS=(--no-windows)
else
  echo "Using DISPLAY=$DISPLAY for OpenCV preview windows."
  RUN_ARGS=()
fi

echo "== Running Habitat-Sim camera sensor scene =="
rm -rf outputs
"$MICROMAMBA" run -n "$ENV_NAME" python camera_sensor_scene.py "${RUN_ARGS[@]}"

echo "== Normalizing videos for browser playback =="
FFMPEG_MODE=""
FFMPEG_BIN=""
for candidate in ffmpeg /usr/bin/ffmpeg /usr/local/bin/ffmpeg; do
  if command -v "$candidate" >/dev/null 2>&1; then
    resolved="$(command -v "$candidate")"
  elif [[ -x "$candidate" ]]; then
    resolved="$candidate"
  else
    continue
  fi
  encoders="$("$resolved" -hide_banner -encoders 2>/dev/null || true)"
  if grep -q "libx264" <<<"$encoders"; then
    FFMPEG_MODE="system"
    FFMPEG_BIN="$resolved"
    break
  fi
done

if [[ "$FFMPEG_MODE" == "system" ]]; then
  :
else
  encoders="$("$MICROMAMBA" run -n "$ENV_NAME" ffmpeg -hide_banner -encoders 2>/dev/null || true)"
  if grep -q "libx264" <<<"$encoders"; then
    FFMPEG_MODE="mamba"
  else
    echo "ERROR: ffmpeg with libx264 is required to create browser-playable MP4 files." >&2
    echo "Install system ffmpeg with libx264, or use a Conda ffmpeg build that includes libx264." >&2
    exit 1
  fi
fi

run_ffmpeg() {
  if [[ "$FFMPEG_MODE" == "system" ]]; then
    "$FFMPEG_BIN" "$@"
  else
    "$MICROMAMBA" run -n "$ENV_NAME" ffmpeg "$@"
  fi
}

for video in outputs/videos/external_rgb_stream.mp4 \
  outputs/videos/external_depth_stream.mp4 \
  outputs/videos/external_rgb_depth_side_by_side.mp4 \
  outputs/videos/habitat_overview.mp4; do
  tmp="${video%.mp4}.browser.mp4"
  run_ffmpeg -y -loglevel error \
    -i "$video" \
    -an \
    -c:v libx264 \
    -profile:v baseline \
    -level 3.1 \
    -pix_fmt yuv420p \
    -movflags +faststart \
    "$tmp"
  mv "$tmp" "$video"
done

test -s outputs/screenshots/habitat_overview.png
test -s outputs/screenshots/external_rgb_window.png
test -s outputs/screenshots/external_depth_window.png
test -s outputs/videos/external_rgb_stream.mp4
test -s outputs/videos/external_depth_stream.mp4
test -s outputs/videos/external_rgb_depth_side_by_side.mp4
test -s outputs/videos/habitat_overview.mp4

echo "Verified: Habitat-Sim overview output was generated."
echo "Verified: wrist RGB output was generated."
echo "Verified: wrist depth output was generated."
