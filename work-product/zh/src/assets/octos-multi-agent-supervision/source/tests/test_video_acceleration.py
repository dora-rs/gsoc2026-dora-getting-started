from pathlib import Path

import pytest

from process_runtime.video_acceleration import build_ffmpeg_command


def test_ffmpeg_command_accelerates_without_scaling_or_audio() -> None:
    command = build_ffmpeg_command(
        Path("raw.mp4"),
        Path("tutorial-2.5x.mp4"),
        speed=2.5,
    )

    assert command[:4] == ["ffmpeg", "-y", "-i", "raw.mp4"]
    assert ["-vf", "setpts=PTS/2.5"] == command[4:6]
    assert "-an" in command
    assert ["-vsync", "vfr"] == command[-5:-3]
    assert "-fps_mode" not in command
    assert "scale" not in " ".join(command)
    assert command[-1] == "tutorial-2.5x.mp4.tmp.mp4"


@pytest.mark.parametrize("speed", [1.0, 0.0, -2.0])
def test_ffmpeg_command_rejects_non_accelerating_speed(speed: float) -> None:
    with pytest.raises(ValueError, match="greater than 1"):
        build_ffmpeg_command(
            Path("raw.mp4"),
            Path("tutorial.mp4"),
            speed=speed,
        )
