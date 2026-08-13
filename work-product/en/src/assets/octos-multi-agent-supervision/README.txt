# Dora and Octos Process Supervision

This reference project runs a continuous temperature and pressure supervision
task with two simulated mobile manipulators:

- the Observer robot docks at the sensor station, reads pressure through Dora,
  and reads the temperature display through RGB and a local VLM;
- the Operator robot uses named cooling and relief switch actions;
- the Supervisor uses Octos and a local coding model to author and review a
  restricted adaptive strategy.

The model chooses observations, timing, and switch requests. Dora transports
state and action receipts. Deterministic validation and simulator interlocks
remain responsible for execution and hard safety limits.

## Requirements

- Ubuntu 22.04 with an NVIDIA GPU and working X11 display
- Docker Engine and NVIDIA Container Toolkit
- Dora CLI 1.0.0-rc.4 and `dora-rs==1.0.0rc4`
- Python 3.11.14 for Dora sidecars; system Python 3.10 for ROS 2 and application workers
- Webots R2025a and ROS 2 Humble, supplied by the container
- Octos 2.0.2
- Ollama 0.32.1
- `qwen3-vl:8b-instruct` and `qwen2.5-coder:7b`

## Reproduce

```bash
npm install -g @octos-org/octos@2.0.2
octos --version

ollama pull qwen3-vl:8b-instruct
ollama pull qwen2.5-coder:7b
bash tutorial.sh run
```

Read `VERSIONS.md`, `TUTORIAL_CONTRACT.md`, and `ASSET_GUIDE.md` before the
run. The entry builds the image when missing and owns Webots, Dora, all three
Octos roles, recording, verification, and cleanup. Component scripts remain
for source inspection and are not alternative reproduction entries.

The task has no natural completion. Press `Ctrl+C` after observing the desired
number of cooling and relief cycles. The shutdown path requests both controls
off before the runner exits.

## Test

Inside the container:

```bash
cd /workspace
/usr/bin/python3 -m pytest -q
```

Runtime output is written below `outputs/` and is ignored by Git.
