def observer_is_docked(state: dict) -> bool:
    return (
        state.get("location") == "station"
        and state.get("docked") is True
    )


def pressure_is_available(reading: dict) -> bool:
    return (
        reading.get("available") is True
        and isinstance(reading.get("value_kpa"), (int, float))
    )
