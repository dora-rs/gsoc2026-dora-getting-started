# LLM Action Planning Reference Project

This project contains the validated Webots scene, robot controllers, Dora
dataflow, skill runtime, model clients, JSON validators, and focused tests used
by the tutorial.

## Requirements

- Ubuntu 22.04 x86_64 with an X11 desktop
- Docker with NVIDIA Container Toolkit when GPU rendering is used
- NVIDIA driver compatible with the Webots R2025a container
- Dora CLI 0.5.0 at `${HOME}/.cargo/bin/dora`
- Ollama 0.12.0 or newer on the host
- `qwen3-vl:8b-instruct` pulled in Ollama

## Run

```bash
ollama pull qwen3-vl:8b-instruct
docker build -t week9-webots-llm:humble .
chmod +x run-container.sh launch-webots.sh
./run-container.sh
```

In the container, start Webots:

```bash
./launch-webots.sh
```

In a second container shell, run tests and the Dora dataflow:

```bash
cd /workspace
pytest -q
cd dora
dora run dataflow.yml
```

The planner calls Ollama through `http://127.0.0.1:11434` by default because
the container uses host networking. Override `OLLAMA_URL`, `OLLAMA_MODEL`, or
`WEEK9_OUTPUT_DIR` when needed.

The world pins the official Webots R2025a
[youBot model](https://github.com/cyberbotics/webots/tree/R2025a/projects/robots/kuka/youbot).
The custom scene and application code are provided for tutorial reproduction.
