import pytest

from week11_runtime.vlm_contract import (
    build_temperature_vlm_request,
    parse_temperature_result,
)


def test_temperature_result_requires_structured_visible_reading() -> None:
    result = parse_temperature_result(
        '{"visible":true,"temperature_c":46.0,'
        '"confidence":0.98,"evidence":"display reads 46.0 C"}'
    )

    assert result.visible
    assert result.temperature_c == 46.0
    assert result.confidence == 0.98


def test_temperature_result_rejects_missing_value_when_visible() -> None:
    with pytest.raises(ValueError, match="temperature_c"):
        parse_temperature_result(
            '{"visible":true,"confidence":0.9,"evidence":"display visible"}'
        )


def test_temperature_result_rejects_out_of_range_confidence() -> None:
    with pytest.raises(ValueError, match="confidence"):
        parse_temperature_result(
            '{"visible":true,"temperature_c":46.0,'
            '"confidence":1.4,"evidence":"display reads 46.0 C"}'
        )


def test_temperature_request_releases_visual_model_after_response() -> None:
    payload = build_temperature_vlm_request(
        encoded_image="encoded-image",
        model="qwen3-vl:8b-instruct",
        prompt="read the display",
    )

    assert payload["keep_alive"] == 0
    assert payload["messages"][0]["images"] == ["encoded-image"]
