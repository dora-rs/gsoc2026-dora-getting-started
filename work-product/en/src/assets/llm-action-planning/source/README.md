# LLM Action Planning Reference Project

This project contains the validated Webots scene, robot controllers, Dora
dataflow, skill runtime, model clients, JSON validators, and focused tests used
by the tutorial.

## Requirements

- Ubuntu 22.04 x86_64 with an X11 desktop
- Docker with NVIDIA Container Toolkit when GPU rendering is used
- NVIDIA driver compatible with the Webots R2025a container
- Dora CLI 1.0.0-rc.4 and `dora-rs==1.0.0rc4`, installed in the container
- Python 3.11.14 for Dora sidecars; system Python 3.10 for ROS 2 and application workers
- Ollama 0.32.1 on the host
- `qwen3-vl:8b-instruct` pulled in Ollama

## Reproduce

Pull the pinned host model, read `VERSIONS.md`, `TUTORIAL_CONTRACT.md`, and
`ASSET_GUIDE.md`, then use the single supported project entry:

```bash
ollama pull qwen3-vl:8b-instruct
bash tutorial.sh run
```

The entry builds the container image when missing, starts Webots and Dora,
runs the tests and mission, verifies the visual state transition and return
home, and cleans up. Component scripts are implementation references, not
alternative reproduction entries.

The planner calls Ollama through `http://127.0.0.1:11434` by default because
the container uses host networking. Override `OLLAMA_URL`, `OLLAMA_MODEL`, or
`ACTION_PLANNING_OUTPUT_DIR` when needed.

The world pins the official Webots R2025a
[youBot model](https://github.com/cyberbotics/webots/tree/R2025a/projects/robots/kuka/youbot).
The custom scene and application code are provided for tutorial reproduction.
