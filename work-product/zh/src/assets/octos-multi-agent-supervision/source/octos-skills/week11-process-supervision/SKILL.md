---
name: week11-process-supervision
description: Supervise the Dora two-robot temperature and pressure process cell.
version: 1.0.0
author: qiyang-tan
always: true
---

# Dora Process Supervision

Use these atomic tools instead of shell commands or direct ROS access.

## Roles

- **Supervisor** coordinates the mission and delegates work. It does not read
  sensors or operate switches directly.
- **Observer** owns the observer robot, pressure sensor, RGB camera, and local
  VLM temperature reading.
- **Operator** owns the operator robot and the cooling and relief switches.

The process starts immediately with the simulation. Dispatch Observer and
Operator concurrently, and keep their role boundaries visible in activity
reports.

## Safety And Timing

- Temperature is safe inside 30-60 C.
- Pressure is safe inside 160-200 kPa.
- Hard limits are handled by the Dora/Webots safety layer, not by the agent.
- Use values, timestamps, observed rates, action history, and data freshness to
  choose when to observe and which sensors are needed.
- Use `wait_seconds` for the interval you choose.
- A temperature reading always requests a fresh RGB frame and local VLM call.
- Verify the effect of a switch with later observations. Do not assume it
  worked only because the command succeeded.
- Use `apply_switch_actions` for immediate independent valve changes. Reobserve
  the process before deciding when to reverse those changes.
- Pass through the exact `action_id` supplied in the task. Reusing that ID
  returns the original receipt without repeating physical actions.

## Recommended Mission

1. Report the current role and action.
2. Place Observer and Operator at their named stations concurrently.
3. Ask Observer only for the sensor readings selected by the current strategy.
4. Analyze timestamped history, rates, freshness, and current valve states.
5. Delegate immediate state changes to Operator with `apply_switch_actions`.
6. Reobserve and dynamically decide whether to keep or reverse each control.
7. Continue supervision until the external validation process stops the run.

Do not request coordinates, wheel speeds, joint angles, hidden simulator
variables, or direct process truth.
