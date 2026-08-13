#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

from controller import Supervisor

import rclpy
from std_msgs.msg import String


TIME_STEP = 32
WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from process_runtime.plant_model import (
    PlantModel,
    plant_config_from_environment,
)
from process_runtime.control_cycles import (
    ControlCycleTracker,
    ControlEngagementTracker,
)
from process_runtime.scene_display import gauge_fill_width
class PlantDisplayController:
    def __init__(self) -> None:
        self.robot = Supervisor()
        self.node = rclpy.create_node("process_plant_display")
        self.model = PlantModel(plant_config_from_environment(os.environ))
        self.model.start()
        self.cycle_tracker = ControlCycleTracker()
        self.engagement_tracker = ControlEngagementTracker()
        self.engagement_counts = {"cooling": 0, "relief": 0}
        self.display = self.robot.getDevice("temperature_display")
        self.cooling_lever = self.robot.getFromDef("COOLING_SWITCH_LEVER")
        self.relief_lever = self.robot.getFromDef("RELIEF_SWITCH_LEVER")
        self.cooling_indicator = self.robot.getFromDef("COOLING_INDICATOR")
        self.relief_indicator = self.robot.getFromDef("RELIEF_INDICATOR")
        self.observer_docked = False
        self.operator_at_control = False
        self.observer_location = "home"
        self.operator_location = "home"
        self.agent_action = "Waiting for Octos"
        self.state_pub = self.node.create_publisher(
            String, "/process/plant/state", 10
        )
        self.pressure_pub = self.node.create_publisher(
            String, "/process/plant/pressure", 10
        )
        self.node.create_subscription(
            String,
            "/process/operator/switch_event",
            self.on_switch_event,
            10,
        )
        self.node.create_subscription(
            String,
            "/process/observer/state",
            self.on_observer_state,
            10,
        )
        self.node.create_subscription(
            String,
            "/process/operator/state",
            self.on_operator_state,
            10,
        )
        self.node.create_subscription(
            String,
            "/process/agent_activity",
            self.on_agent_activity,
            10,
        )
        self.last_time = self.robot.getTime()
        self.last_draw_second = -1
        self._draw_temperature()
        self._update_switch_visuals()

    @staticmethod
    def _decode(message: String) -> dict:
        try:
            return json.loads(message.data)
        except json.JSONDecodeError:
            return {}

    def on_switch_event(self, message: String) -> None:
        event = self._decode(message)
        switch = event.get("switch")
        enabled = event.get("enabled")
        if switch == "cooling" and isinstance(enabled, bool):
            self.model.set_cooling(enabled)
        elif switch == "relief" and isinstance(enabled, bool):
            self.model.set_relief(enabled)
        self._update_switch_visuals()

    def on_observer_state(self, message: String) -> None:
        state = self._decode(message)
        self.observer_docked = bool(state.get("docked"))
        self.observer_location = str(
            state.get("location") or self.observer_location
        )

    def on_operator_state(self, message: String) -> None:
        state = self._decode(message)
        self.operator_at_control = bool(
            state.get("at_control")
        )
        self.operator_location = str(
            state.get("location") or self.operator_location
        )

    def on_agent_activity(self, message: String) -> None:
        self.agent_action = message.data[:96]

    def _set_indicator(self, node, enabled: bool, color: list[float]) -> None:
        off = [0.025, 0.03, 0.035]
        node.getField("baseColor").setSFColor(color if enabled else off)
        node.getField("emissiveColor").setSFColor(
            color if enabled else off
        )

    def _update_switch_visuals(self) -> None:
        state = self.model.state
        cooling_angle = 0.85 if state.cooling_on else -0.55
        relief_angle = 0.85 if state.relief_open else -0.55
        self.cooling_lever.getField("rotation").setSFRotation(
            [0.0, 1.0, 0.0, cooling_angle]
        )
        self.relief_lever.getField("rotation").setSFRotation(
            [0.0, 1.0, 0.0, relief_angle]
        )
        self._set_indicator(
            self.cooling_indicator, state.cooling_on, [0.05, 0.75, 1.0]
        )
        self._set_indicator(
            self.relief_indicator, state.relief_open, [1.0, 0.68, 0.05]
        )

    def _draw_temperature(self) -> None:
        value = self.model.state.temperature_c
        width = self.display.getWidth()
        height = self.display.getHeight()
        self.display.setColor(0x101820)
        self.display.fillRectangle(0, 0, width, height)
        self.display.setColor(0xD7E4EA)
        self.display.setFont("Arial", 24, True)
        self.display.drawText("TEMPERATURE SENSOR", 20, 18)
        self.display.setFont("Arial", 72, True)
        self.display.setColor(0xFFFFFF)
        self.display.drawText(f"{value:04.1f} C", 54, 70)
        self.display.setFont("Arial", 25, True)
        self.display.setColor(0x8FA3AD)
        self.display.drawText("SAFE RANGE: 30.0 - 60.0 C", 42, 164)
        fraction = max(0.0, min(1.0, (value - 25.0) / 45.0))
        self.display.setColor(0x26343B)
        self.display.fillRectangle(26, 210, width - 52, 28)
        color = (
            0x2CCB8A
            if self.model.config.temperature_safe_min_c
            <= value
            <= self.model.config.temperature_safe_max_c
            else 0xF04D3A
        )
        self.display.setColor(color)
        fill_width = gauge_fill_width(
            fraction, maximum_width=width - 52
        )
        if fill_width is not None:
            self.display.fillRectangle(26, 210, fill_width, 28)
        image = self.display.imageCopy(0, 0, width, height)
        self.display.imageSave(
            image, "/workspace/outputs/temperature-display.png"
        )
        self.display.imageDelete(image)

    def _publish_state(self) -> None:
        state = self.model.state
        temperature_rate = self.model.config.heating_rate_c_per_s
        if state.cooling_on:
            temperature_rate += self.model.config.cooling_effect_c_per_s
        pressure_rate = self.model.config.pressure_rate_kpa_per_s
        if state.relief_open:
            pressure_rate += self.model.config.relief_effect_kpa_per_s
        payload = {
            "simulation_time_s": state.elapsed_s,
            "temperature_c": round(state.temperature_c, 3),
            "pressure_kpa": round(state.pressure_kpa, 3),
            "temperature_safe_min_c": self.model.config.temperature_safe_min_c,
            "temperature_safe_max_c": self.model.config.temperature_safe_max_c,
            "pressure_safe_min_kpa": self.model.config.pressure_safe_min_kpa,
            "pressure_safe_max_kpa": self.model.config.pressure_safe_max_kpa,
            "temperature_rate_c_per_s": round(temperature_rate, 3),
            "pressure_rate_kpa_per_s": round(pressure_rate, 3),
            "temperature_hard_min_c": self.model.config.temperature_hard_min_c,
            "temperature_hard_max_c": self.model.config.temperature_hard_max_c,
            "pressure_hard_min_kpa": self.model.config.pressure_hard_min_kpa,
            "pressure_hard_max_kpa": self.model.config.pressure_hard_max_kpa,
            "cooling_on": state.cooling_on,
            "relief_open": state.relief_open,
            "observer_docked": self.observer_docked,
            "observer_location": self.observer_location,
            "operator_at_control": self.operator_at_control,
            "operator_location": self.operator_location,
            "phase": state.phase,
            "emergency_reason": state.emergency_reason,
            "agent_action": self.agent_action,
        }
        payload["control_cycle_count"] = self.cycle_tracker.update(payload)
        self.engagement_counts = self.engagement_tracker.update(payload)
        payload["cooling_engagement_count"] = self.engagement_counts[
            "cooling"
        ]
        payload["relief_engagement_count"] = self.engagement_counts[
            "relief"
        ]
        payload["engagement_target"] = 2
        self.state_pub.publish(String(data=json.dumps(payload)))
        pressure = {
            "available": self.observer_docked,
            "value_kpa": (
                round(state.pressure_kpa, 3)
                if self.observer_docked
                else None
            ),
            "error_code": (
                None if self.observer_docked else "OBSERVER_NOT_DOCKED"
            ),
            "simulation_time_s": state.elapsed_s,
        }
        self.pressure_pub.publish(String(data=json.dumps(pressure)))

    def _draw_hud(self) -> None:
        state = self.model.state
        safe_t = (
            self.model.config.temperature_safe_min_c
            <= state.temperature_c
            <= self.model.config.temperature_safe_max_c
        )
        safe_p = (
            self.model.config.pressure_safe_min_kpa
            <= state.pressure_kpa
            <= self.model.config.pressure_safe_max_kpa
        )
        color_t = 0x42E6A4 if safe_t else 0xFF5A47
        color_p = 0x42E6A4 if safe_p else 0xFF5A47
        self.robot.setLabel(
            0, "OCTOS MULTI-AGENT PROCESS SUPERVISION", 0.02, 0.03,
            0.026, 0xFFFFFF, 0.0, "Arial"
        )
        self.robot.setLabel(
            1,
            f"TEMP {state.temperature_c:05.1f} C  SAFE 30-60",
            0.02, 0.075, 0.024, color_t, 0.0, "Arial"
        )
        self.robot.setLabel(
            2,
            f"PRESS {state.pressure_kpa:05.1f} kPa  SAFE 160-200",
            0.02, 0.112, 0.024, color_p, 0.0, "Arial"
        )
        self.robot.setLabel(
            3,
            (
                f"COOLING {'ON' if state.cooling_on else 'OFF'}   "
                f"RELIEF {'OPEN' if state.relief_open else 'CLOSED'}"
            ),
            0.02, 0.149, 0.022, 0xFFFFFF, 0.0, "Arial"
        )
        self.robot.setLabel(
            4,
            (
                f"OBSERVER {'DOCKED' if self.observer_docked else 'MOVING'}   "
                f"OPERATOR {'READY' if self.operator_at_control else 'MOVING'}   "
                f"COOLING {self.engagement_counts['cooling']}/2   "
                f"RELIEF {self.engagement_counts['relief']}/2"
            ),
            0.02, 0.184, 0.021, 0xC8D5DC, 0.0, "Arial"
        )
        self.robot.setLabel(
            5, f"OCTOS: {self.agent_action}", 0.02, 0.222,
            0.021, 0x72B7FF, 0.0, "Arial"
        )

    def run(self) -> None:
        counter = 0
        while self.robot.step(TIME_STEP) != -1:
            rclpy.spin_once(self.node, timeout_sec=0.0)
            now = self.robot.getTime()
            dt = now - self.last_time
            self.last_time = now
            if self.model.state.phase == "running":
                self.model.step(dt)
            second = int(now)
            if second != self.last_draw_second:
                self.last_draw_second = second
                self._draw_temperature()
                self._draw_hud()
            counter += 1
            if counter % 8 == 0:
                self._publish_state()
        self.node.destroy_node()


def main() -> None:
    rclpy.init(args=sys.argv)
    controller = PlantDisplayController()
    try:
        controller.run()
    finally:
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
