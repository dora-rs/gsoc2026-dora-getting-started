# Multimodal Pick-and-Place Verification

This directory contains the reproducible code behind the multimodal visual
inspection chapter. Dora and model-control nodes run on Python 3.11; the
Habitat-Sim worker runs on Python 3.9 behind a structured JSONL bridge.

## Verified Environment

- Ubuntu 22.04.5 LTS, x86_64
- NVIDIA driver 580.159.03
- Dora CLI 1.0.0-rc.4 and `dora-rs==1.0.0rc4`
- Habitat-Sim 0.3.3
- Dora runtime Python 3.11.14
- Habitat-Sim worker Python 3.9.23
- NumPy 1.26.4
- SciPy 1.13.1
- OpenCV 4.12.0
- Trimesh 4.7.4
- Ollama 0.32.1
- `qwen3-vl:8b-instruct`, Q4_K_M

## Layout

- `assets/`: Franka URDF and Apache-2.0 mesh assets with source metadata.
- `contracts.py`: closed visual-result contract and validation.
- `controller.py`: task state machine independent of Dora transport.
- `scene.py`: Habitat-Sim scene, cameras, arm, and cube objects.
- `trajectory.py`: interpolation, joint validation, and IK helpers.
- `prepare_trajectory.py`: validates camera visibility and solves waypoints.
- `simulation_runtime.py`: deterministic motion and synchronized recording.
- `simulation_bridge_node.py` and `simulation_worker.py`: isolated runtime boundary.
- `*_node.py` and `dataflow.yml`: complete Dora application.
- `tests/`: focused unit tests for contracts, state transitions, and motion.

Generated files are written under `outputs/`. The supplied URDF, Franka meshes,
validated trajectory, source scripts, and tests are the fixed reference inputs.

## Focused Verification

The supplied run script creates or reuses two isolated micromamba environments.
Run the tests and simulator without a model service:

```bash
SIMULATION_ONLY=1 bash run.sh
```

## Dora Run

Start Ollama on localhost and ensure the pinned vision model is available. Then
run the complete workflow. Do not place model caches, credentials, or
machine-specific paths in this folder.

```bash
export OLLAMA_MODEL=qwen3-vl:8b-instruct
export OLLAMA_URL=http://127.0.0.1:11434
bash run.sh
```

A successful run prints the initial visual result, motion result, final visual
result, and `TASK_SUCCESS`, then all three nodes exit.
