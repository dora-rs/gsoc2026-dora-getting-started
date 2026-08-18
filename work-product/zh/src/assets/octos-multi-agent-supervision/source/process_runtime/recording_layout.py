from __future__ import annotations

from typing import Any

import cv2
import numpy as np


CANVAS_WIDTH = 1920
CANVAS_HEIGHT = 720
VIEW_WIDTH = 960
VIEW_HEIGHT = 540
COLOR_SAFE = (139, 203, 44)
COLOR_DANGER = (58, 85, 240)
COLOR_NEUTRAL = (67, 78, 84)
COLOR_COOLING = (255, 196, 55)
COLOR_RELIEF = (40, 180, 255)


def recorder_should_stop(
    telemetry: dict,
    engagement_counts: dict[str, int],
    *,
    completion_gate,
    now: float,
) -> bool:
    return completion_gate.update(telemetry, engagement_counts, now=now)


def robot_status_label(
    location: str,
    at_station: bool,
    station_label: str,
) -> str:
    if at_station:
        return station_label
    if location == "home":
        return "HOME"
    return "MOVING"


def valve_indicator_color(switch: str, active: bool) -> tuple[int, int, int]:
    if not active:
        return COLOR_NEUTRAL
    if switch == "cooling":
        return COLOR_COOLING
    if switch == "relief":
        return COLOR_RELIEF
    raise ValueError(f"unknown switch: {switch}")


def engagement_progress_labels(telemetry: dict) -> tuple[str, str]:
    target = max(1, int(telemetry.get("engagement_target", 2)))
    cooling = min(
        int(telemetry.get("cooling_engagement_count", 0)),
        target,
    )
    relief = min(
        int(telemetry.get("relief_engagement_count", 0)),
        target,
    )
    return (
        f"COOLING {cooling}/{target}",
        f"RELIEF {relief}/{target}",
    )


def _fit_view(frame: np.ndarray) -> np.ndarray:
    height, width = frame.shape[:2]
    source_ratio = width / height
    target_ratio = VIEW_WIDTH / VIEW_HEIGHT
    if source_ratio > target_ratio:
        crop_width = int(height * target_ratio)
        left = (width - crop_width) // 2
        frame = frame[:, left : left + crop_width]
    elif source_ratio < target_ratio:
        crop_height = int(width / target_ratio)
        top = (height - crop_height) // 2
        frame = frame[top : top + crop_height, :]
    return cv2.resize(
        frame,
        (VIEW_WIDTH, VIEW_HEIGHT),
        interpolation=cv2.INTER_AREA,
    )


def _label(frame: np.ndarray, text: str, x: int) -> None:
    cv2.rectangle(
        frame,
        (x + 18, 16),
        (x + 280, 60),
        (21, 29, 34),
        -1,
    )
    cv2.putText(
        frame,
        text,
        (x + 34, 47),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.78,
        (242, 246, 248),
        2,
        cv2.LINE_AA,
    )


def _metric(
    frame: np.ndarray,
    *,
    x: int,
    title: str,
    value: float | None,
    minimum: float,
    maximum: float,
    rate: float,
    unit: str,
) -> None:
    safe = (
        value is not None
        and minimum <= value <= maximum
    )
    color = COLOR_SAFE if safe else COLOR_DANGER
    value_text = "--" if value is None else f"{value:.1f}"
    cv2.putText(
        frame,
        title,
        (x, 578),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.54,
        (159, 175, 184),
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        frame,
        f"{value_text} {unit}",
        (x, 623),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.08,
        color,
        3,
        cv2.LINE_AA,
    )
    cv2.putText(
        frame,
        f"SAFE {minimum:.0f}-{maximum:.0f} {unit}",
        (x, 656),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.52,
        (205, 213, 217),
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        frame,
        f"TREND {rate:+.2f} {unit}/s",
        (x, 688),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.50,
        (159, 175, 184),
        1,
        cv2.LINE_AA,
    )


def _valve_indicator(
    frame: np.ndarray,
    *,
    x: int,
    switch: str,
    active: bool,
) -> None:
    color = valve_indicator_color(switch, active)
    cv2.rectangle(frame, (x, 574), (x + 226, 630), color, -1)
    label = switch.upper()
    state = (
        "ON"
        if switch == "cooling" and active
        else "OPEN"
        if switch == "relief" and active
        else "OFF"
        if switch == "cooling"
        else "CLOSED"
    )
    text_color = (16, 23, 27) if active else (236, 241, 243)
    cv2.putText(
        frame,
        label,
        (x + 12, 596),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.46,
        text_color,
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        frame,
        state,
        (x + 12, 621),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.70,
        text_color,
        2,
        cv2.LINE_AA,
    )


def compose_recording_frame(
    scene: np.ndarray,
    observer: np.ndarray,
    telemetry: dict[str, Any],
) -> np.ndarray:
    canvas = np.full(
        (CANVAS_HEIGHT, CANVAS_WIDTH, 3),
        (20, 27, 31),
        dtype=np.uint8,
    )
    canvas[:VIEW_HEIGHT, :VIEW_WIDTH] = _fit_view(scene)
    canvas[:VIEW_HEIGHT, VIEW_WIDTH:] = _fit_view(observer)
    canvas[:VIEW_HEIGHT, VIEW_WIDTH - 2 : VIEW_WIDTH + 2] = (
        225,
        232,
        235,
    )
    _label(canvas, "PROCESS CELL", 0)
    _label(canvas, "OBSERVER RGB", VIEW_WIDTH)

    temperature = telemetry.get("temperature_c")
    pressure = telemetry.get("pressure_kpa")
    _metric(
        canvas,
        x=34,
        title="TEMPERATURE",
        value=float(temperature) if temperature is not None else None,
        minimum=float(telemetry.get("temperature_safe_min_c", 30.0)),
        maximum=float(telemetry.get("temperature_safe_max_c", 60.0)),
        rate=float(telemetry.get("temperature_rate_c_per_s", 0.0)),
        unit="C",
    )
    _metric(
        canvas,
        x=330,
        title="PRESSURE",
        value=float(pressure) if pressure is not None else None,
        minimum=float(telemetry.get("pressure_safe_min_kpa", 160.0)),
        maximum=float(telemetry.get("pressure_safe_max_kpa", 200.0)),
        rate=float(telemetry.get("pressure_rate_kpa_per_s", 0.0)),
        unit="kPa",
    )

    _valve_indicator(
        canvas,
        x=650,
        switch="cooling",
        active=bool(telemetry.get("cooling_on")),
    )
    _valve_indicator(
        canvas,
        x=892,
        switch="relief",
        active=bool(telemetry.get("relief_open")),
    )

    observer_state = robot_status_label(
        str(telemetry.get("observer_location") or ""),
        bool(telemetry.get("observer_docked")),
        "DOCKED",
    )
    operator_state = robot_status_label(
        str(telemetry.get("operator_location") or ""),
        bool(telemetry.get("operator_at_control")),
        "READY",
    )
    cv2.putText(
        canvas,
        f"OBSERVER {observer_state}  |  OPERATOR {operator_state}",
        (650, 671),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (185, 199, 206),
        1,
        cv2.LINE_AA,
    )
    progress_labels = engagement_progress_labels(telemetry)
    target = max(1, int(telemetry.get("engagement_target", 2)))
    progress_counts = (
        int(telemetry.get("cooling_engagement_count", 0)),
        int(telemetry.get("relief_engagement_count", 0)),
    )
    for x, label, count, color in (
        (650, progress_labels[0], progress_counts[0], COLOR_COOLING),
        (892, progress_labels[1], progress_counts[1], COLOR_RELIEF),
    ):
        cv2.putText(
            canvas,
            label,
            (x, 704),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.58,
            COLOR_SAFE if count >= target else color,
            2,
            cv2.LINE_AA,
        )

    activity = str(telemetry.get("agent_action") or "Waiting for Octos")
    if len(activity) > 58:
        activity = activity[:55] + "..."
    cv2.putText(
        canvas,
        "OCTOS MULTI-AGENT ACTIVITY",
        (1190, 582),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.56,
        (77, 182, 255),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        canvas,
        activity,
        (1190, 630),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.61,
        (239, 243, 245),
        2,
        cv2.LINE_AA,
    )
    phase = str(telemetry.get("phase") or "starting").upper()
    cv2.putText(
        canvas,
        f"PROCESS {phase}",
        (1190, 677),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.54,
        (168, 184, 192),
        1,
        cv2.LINE_AA,
    )
    return canvas
