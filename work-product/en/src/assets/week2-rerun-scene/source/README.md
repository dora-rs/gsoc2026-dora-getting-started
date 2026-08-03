# Rerun Scene Verification

This example runs a small Dora dataflow that sends scene state into a Rerun
visualizer. The visualizer writes `artifacts/dora_rerun_scene.rrd` and uses
reusable glTF assets for the robot and car. On a desktop session, `run.sh` also
captures a Rerun Viewer screenshot and a short recording.

```bash
bash run.sh
```

On a headless machine, skip only the desktop capture while still generating
and checking the `.rrd` recording:

```bash
CAPTURE_VIEWER=0 bash run.sh
```

The two glTF models are supplied in `models/`. `generate_models.py` is retained
so their deterministic construction can be inspected or repeated with
`REGENERATE_MODELS=1 bash run.sh`. The default run uses the supplied files.
Generated
recordings under `artifacts/`, runtime logs under `logs/`, Dora sessions under
`out/`, and `.venv/` are local outputs and are not part of the reference input.
