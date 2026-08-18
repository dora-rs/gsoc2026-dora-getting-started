from process_runtime.scene_display import (
    DisplayState,
    build_hud_lines,
    gauge_fill_width,
    gauge_fraction,
)


def test_temperature_gauge_fraction_is_clamped() -> None:
    assert gauge_fraction(50.0, minimum=40.0, maximum=70.0) == 1 / 3
    assert gauge_fraction(20.0, minimum=40.0, maximum=70.0) == 0.0
    assert gauge_fraction(90.0, minimum=40.0, maximum=70.0) == 1.0


def test_empty_gauge_does_not_request_a_zero_width_rectangle() -> None:
    assert gauge_fill_width(0.0, maximum_width=460) is None
    assert gauge_fill_width(0.5, maximum_width=460) == 230


def test_hud_contains_process_ranges_switches_and_agent_action() -> None:
    lines = build_hud_lines(
        DisplayState(
            temperature_c=58.4,
            pressure_kpa=196.2,
            temperature_safe_min_c=30.0,
            temperature_safe_max_c=60.0,
            pressure_safe_min_kpa=160.0,
            pressure_safe_max_kpa=200.0,
            temperature_rate_c_per_s=0.22,
            pressure_rate_kpa_per_s=-2.20,
            cooling_on=True,
            relief_open=False,
            observer_status="DOCKED",
            operator_status="AT CONTROL",
            agent_action="Observer requested a fresh camera frame",
            cooling_engagement_count=1,
            relief_engagement_count=2,
            engagement_target=2,
        )
    )

    text = "\n".join(lines)
    assert "58.4 C  SAFE 30-60 C" in text
    assert "196.2 kPa  SAFE 160-200 kPa" in text
    assert "+0.22 C/s" in text
    assert "-2.20 kPa/s" in text
    assert "COOLING ON" in text
    assert "RELIEF CLOSED" in text
    assert "COOLING 1/2" in text
    assert "RELIEF 2/2" in text
    assert "Observer requested a fresh camera frame" in text
