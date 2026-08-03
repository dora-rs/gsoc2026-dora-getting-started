import pytest
from pydantic import ValidationError

from week10_runtime.indicator_vision import IndicatorObservation


def test_visible_indicator_has_boolean_lit_state():
    observation = IndicatorObservation(
        target="status_indicator",
        visible=True,
        lit=True,
        confidence=0.98,
    )
    assert observation.lit is True


def test_occluded_indicator_must_use_unknown_lit_state():
    observation = IndicatorObservation(
        target="status_indicator",
        visible=False,
        lit=None,
        confidence=0.2,
    )
    assert observation.lit is None

    with pytest.raises(ValidationError):
        IndicatorObservation(
            target="status_indicator",
            visible=False,
            lit=True,
            confidence=0.2,
        )


def test_indicator_observation_rejects_extra_fields():
    with pytest.raises(ValidationError):
        IndicatorObservation(
            target="status_indicator",
            visible=True,
            lit=False,
            confidence=0.9,
            switch_state="off",
        )
