import pytest

from week10_runtime.arm_transitions import (
    TransitionRejected,
    switch_state_after_press,
    validate_arm_transition,
)


def test_arm_uses_the_validated_atomic_sequence_at_switch():
    validate_arm_transition("home", "ready", location="main_switch")
    validate_arm_transition("ready", "press", location="main_switch")
    validate_arm_transition("press", "retract", location="main_switch")
    validate_arm_transition("retract", "home", location="main_switch")


def test_arm_cannot_skip_directly_to_press():
    with pytest.raises(TransitionRejected, match="home -> press"):
        validate_arm_transition("home", "press", location="main_switch")


def test_ready_and_press_require_switch_workspace():
    with pytest.raises(TransitionRejected, match="main_switch"):
        validate_arm_transition("home", "ready", location="home")


def test_home_is_an_allowed_recovery_target():
    validate_arm_transition("ready", "home", location="main_switch")
    validate_arm_transition("press", "home", location="main_switch")


def test_press_toggles_the_physical_switch_without_a_target_state_argument():
    assert switch_state_after_press("on") == "off"
    assert switch_state_after_press("off") == "on"
    with pytest.raises(ValueError):
        switch_state_after_press("unknown")
