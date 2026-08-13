# Multimodal Pick-and-Place Verification

This directory contains the reproducible code behind the multimodal visual
inspection chapter. It keeps simulation, model inference, and task control in
separate Dora nodes.

## Verified Environment

- Ubuntu 22.04.5 LTS, x86_64
- NVIDIA driver 580.159.03
- Dora CLI 1.0.0-rc.4 and `dora-rs==1.0.0rc4`
- Habitat-Sim 0.3.3
- Python 3.11 for Dora and Python 3.9 for Habitat-Sim
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
- `*_node.py` and `dataflow.yml`: complete Dora application.
- `tests/`: focused unit tests for contracts, state transitions, and motion.

Generated files are written under `outputs/`, which is ignored by Git. Curated
book images and videos live under each language's `src/assets/` directory.

## Focused Verification

Run the tests first:

```bash
python -m unittest discover -s tests
```

Solve and validate the trajectory:

```bash
python prepare_trajectory.py --output outputs/trajectory
```

Record a simulator-only run:

```bash
python record_demo.py \
  --trajectory outputs/trajectory/trajectory.json \
  --output outputs/demo
```

## Dora Run

Start Ollama on localhost and ensure the pinned vision model is available. Do
not place model caches, credentials, or machine-specific paths in this folder.

```bash
export OLLAMA_MODEL=qwen3-vl:8b-instruct
export OLLAMA_URL=http://127.0.0.1:11434
export WEEK7_TRAJECTORY="$PWD/validated-trajectory.json"
export WEEK7_OUTPUT="$PWD/outputs/dora-run"
dora run dataflow.yml
```

A successful run prints the initial visual result, motion result, final visual
result, and `TASK_SUCCESS`, then all three nodes exit.
