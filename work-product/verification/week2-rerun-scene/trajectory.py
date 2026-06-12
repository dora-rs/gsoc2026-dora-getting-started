from __future__ import annotations

import math

TOTAL_FRAMES = 260

CUBE = {"name": "cube", "x": 0.0, "y": 0.0, "size": 1.0}
CYLINDER = {"name": "cylinder", "x": 4.0, "y": 0.0, "radius": 0.35}

ROBOT_PATH = [
    (-4.0, -0.85),
    (-1.6, -0.85),
    (-0.8, -1.65),
    (0.8, -1.65),
    (1.55, -0.85),
    (3.25, -0.35),
    (3.85, -0.25),
]

CAR_PATH = [
    (-4.4, 0.85),
    (-1.7, 0.85),
    (-0.85, 1.65),
    (0.85, 1.65),
    (1.65, 0.85),
    (3.35, 0.35),
    (4.15, 0.25),
]


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _sample_polyline(points: list[tuple[float, float]], progress: float) -> tuple[float, float, float]:
    progress = max(0.0, min(1.0, progress))
    lengths: list[float] = []
    total = 0.0
    for current, nxt in zip(points, points[1:]):
        segment = math.dist(current, nxt)
        lengths.append(segment)
        total += segment

    target = progress * total
    travelled = 0.0
    for index, segment in enumerate(lengths):
        if travelled + segment >= target:
            local = 0.0 if segment == 0 else (target - travelled) / segment
            x = _lerp(points[index][0], points[index + 1][0], local)
            y = _lerp(points[index][1], points[index + 1][1], local)
            heading = math.atan2(points[index + 1][1] - points[index][1], points[index + 1][0] - points[index][0])
            return x, y, heading
        travelled += segment

    prev, last = points[-2], points[-1]
    return last[0], last[1], math.atan2(last[1] - prev[1], last[0] - prev[0])


def frame_state(frame: int) -> dict:
    robot_progress = min(1.0, max(0.0, (frame - 90) / 70.0))
    car_progress = min(1.0, max(0.0, (frame - 150) / 70.0))

    robot_x, robot_y, robot_heading = _sample_polyline(ROBOT_PATH, robot_progress)
    car_x, car_y, car_heading = _sample_polyline(CAR_PATH, car_progress)

    return {
        "frame": frame,
        "total_frames": TOTAL_FRAMES,
        "objects": {
            "cube": CUBE,
            "cylinder": CYLINDER,
            "robot": {"x": robot_x, "y": robot_y, "heading": robot_heading, "moving": robot_progress < 1.0},
            "car": {"x": car_x, "y": car_y, "heading": car_heading, "moving": car_progress < 1.0},
        },
    }


def all_states() -> list[dict]:
    return [frame_state(frame) for frame in range(TOTAL_FRAMES)]
