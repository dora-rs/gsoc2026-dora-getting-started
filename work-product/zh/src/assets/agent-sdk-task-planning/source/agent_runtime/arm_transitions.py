from __future__ import annotations


class TransitionRejected(ValueError):
    pass


_ALLOWED_TRANSITIONS = {
    ("home", "ready"),
    ("ready", "press"),
    ("press", "retract"),
    ("retract", "home"),
}


def validate_arm_transition(
    current: str, target: str, *, location: str
) -> None:
    if target == "home":
        return
    if target in {"ready", "press"} and location != "main_switch":
        raise TransitionRejected(
            f"{target} requires the robot to be at main_switch"
        )
    if (current, target) not in _ALLOWED_TRANSITIONS:
        raise TransitionRejected(
            f"unsafe arm transition rejected: {current} -> {target}"
        )


def switch_state_after_press(current: str) -> str:
    if current == "on":
        return "off"
    if current == "off":
        return "on"
    raise ValueError("switch state must be known before press")
