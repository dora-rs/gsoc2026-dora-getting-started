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

## Build and run

```bash
ollama pull qwen3-vl:8b-instruct
docker build -t dora-agent-sdk:humble .
chmod +x run-container.sh launch-webots.sh
./run-container.sh
```

Start Webots in the first container shell:

```bash
./launch-webots.sh
```

Start the Dora dataflow in a second shell:

```bash
docker exec -it dora-agent-sdk bash
cd /workspace/dora
dora run dataflow.yml
```

Run the terminal agent in a third shell:

```bash
docker exec -it dora-agent-sdk bash
cd /workspace
/usr/bin/python3 agent_cli.py --task \
  "查看指示灯；如果亮着就关闭开关，确认灯灭后回到起点。"
```

The agent sees only `home`, `indicator_station`, and `main_switch`. Coordinates
remain in `config/locations.json`; arbitrary coordinates, wheel speeds, and
joint angles are not part of the tool schemas.
