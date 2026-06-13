from __future__ import annotations

import os
import re
import subprocess
import time
from pathlib import Path


ARTIFACTS = Path("artifacts")
LOGS = Path("logs")
SCREENSHOT = ARTIFACTS / "rerun_viewer_screenshot.png"
RECORDING = ARTIFACTS / "rerun_viewer_recording.mp4"


def run(command: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(command, check=False, text=True, capture_output=True, **kwargs)


def find_rerun_window(display: str, timeout: float = 12.0) -> int:
    deadline = time.time() + timeout
    pattern = re.compile(r"^\s*(0x[0-9a-fA-F]+)\s+\".*rerun.*\"", re.IGNORECASE)
    while time.time() < deadline:
        result = run(["xwininfo", "-root", "-tree"], env={**os.environ, "DISPLAY": display})
        for line in result.stdout.splitlines():
            match = pattern.search(line)
            if match:
                return int(match.group(1), 16)
        time.sleep(0.4)
    raise RuntimeError("Could not find a Rerun Viewer window.")


def capture(display: str) -> None:
    ARTIFACTS.mkdir(exist_ok=True)
    LOGS.mkdir(exist_ok=True)
    run(["pkill", "-x", "rerun"], env={**os.environ, "DISPLAY": display})
    time.sleep(0.8)
    run(["rerun", "reset"], env={**os.environ, "DISPLAY": display})

    viewer_log = (LOGS / "rerun-viewer-recording.log").open("w", encoding="utf-8")
    viewer = subprocess.Popen(
        ["rerun", "--window-size", "1280x720"],
        stdout=viewer_log,
        stderr=subprocess.STDOUT,
        env={**os.environ, "DISPLAY": display},
    )
    try:
        window_id = find_rerun_window(display)
        time.sleep(3.0)
        live_env = {**os.environ, "DISPLAY": display, "RERUN_LIVE": "1"}
        dataflow = subprocess.Popen(
            ["dora", "run", "dataflow.yml", "--uv", "--stop-after", "13s"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=live_env,
        )
        time.sleep(2.2)

        recorder = subprocess.Popen(
            [
                "ffmpeg",
                "-y",
                "-f",
                "x11grab",
                "-window_id",
                str(window_id),
                "-framerate",
                "10",
                "-i",
                display,
                "-t",
                "10",
                "-vf",
                "scale=960:-2",
                "-an",
                "-pix_fmt",
                "yuv420p",
                str(RECORDING),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env={**os.environ, "DISPLAY": display},
        )
        recorder.communicate()
        dataflow_output, _ = dataflow.communicate(timeout=20)
        (LOGS / "rerun-live-dataflow.log").write_text(dataflow_output, encoding="utf-8")

        run(
            [
                "ffmpeg",
                "-y",
                "-ss",
                "5",
                "-i",
                str(RECORDING),
                "-frames:v",
                "1",
                str(SCREENSHOT),
            ]
        )
    finally:
        viewer.terminate()
        try:
            viewer.wait(timeout=5)
        except subprocess.TimeoutExpired:
            viewer.kill()
        viewer_log.close()


def main() -> None:
    for display in [os.environ.get("DISPLAY"), ":1", ":0"]:
        if not display:
            continue
        try:
            print(f"Trying live Rerun Viewer capture on DISPLAY={display}")
            capture(display)
            if SCREENSHOT.stat().st_size > 0 and RECORDING.stat().st_size > 0:
                print(f"Captured live Rerun Viewer media on DISPLAY={display}")
                return
        except Exception as error:
            print(f"DISPLAY={display} capture failed: {error}")
    raise SystemExit("Could not capture live Rerun Viewer media.")


if __name__ == "__main__":
    main()
