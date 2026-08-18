from __future__ import annotations

import subprocess
from pathlib import Path


def temporary_video_path(output_path: Path) -> Path:
    return output_path.with_name(output_path.name + ".tmp.mp4")


def build_ffmpeg_command(
    input_path: Path,
    output_path: Path,
    *,
    speed: float = 2.5,
) -> list[str]:
    if speed <= 1.0:
        raise ValueError("video speed must be greater than 1")
    temporary_path = temporary_video_path(output_path)
    return [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-vf",
        f"setpts=PTS/{speed:g}",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "23",
        "-vsync",
        "vfr",
        "-movflags",
        "+faststart",
        str(temporary_path),
    ]


def accelerate_video(
    input_path: Path,
    output_path: Path,
    *,
    speed: float = 2.5,
) -> Path:
    if not input_path.is_file():
        raise FileNotFoundError(input_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = temporary_video_path(output_path)
    command = build_ffmpeg_command(
        input_path,
        output_path,
        speed=speed,
    )
    try:
        subprocess.run(command, check=True)
        temporary_path.replace(output_path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
    return output_path
