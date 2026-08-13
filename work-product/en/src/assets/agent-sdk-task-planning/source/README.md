# Agent SDK Task Planning Reference Project

This project contains the validated Webots scene, three named locations,
Dora 1.0.0-rc.4 dataflow, local robot API, OpenAI Agents SDK terminal agent, Ollama
vision classifier, and focused tests used by the tutorial.

## Requirements

- Ubuntu 22.04 x86_64 with an X11 desktop
- Docker with NVIDIA Container Toolkit
- NVIDIA driver compatible with Webots R2025a
- Dora CLI 1.0.0-rc.4 and `dora-rs==1.0.0rc4`, installed in the container
- Python 3.11.14 for Dora sidecars; system Python 3.10 for ROS 2 and application workers
- Ollama with `qwen3-vl:8b-instruct`

## Reproduce

Pull the pinned host model, read `VERSIONS.md`, `TUTORIAL_CONTRACT.md`, and
`ASSET_GUIDE.md`, then use the single supported project entry:

```bash
ollama pull qwen3-vl:8b-instruct
bash tutorial.sh run
```

The entry builds the image when missing and owns Webots, the Dora Robot API,
the Agents SDK task, verification, and cleanup. Component scripts remain for
source inspection and are not alternative reproduction entries.

The agent sees only `home`, `indicator_station`, and `main_switch`. Coordinates
remain in `config/locations.json`; arbitrary coordinates, wheel speeds, and
joint angles are not part of the tool schemas.
