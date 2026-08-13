# Rerun static scene asset guide

Use the supplied models, coordinates, dataflow, and run.sh unchanged.

The only entry command is:

```bash
PYTHON_BIN="$(uv python find 3.11)" \
DISPLAY=:1 CAPTURE_VIEWER=1 bash run.sh
```

Do not set REGENERATE_MODELS. Do not invoke generate_models.py,
capture_rerun_viewer.py, dora, rerun, pip, or uv as an alternative launch
path.

Success requires all of the following:

- `artifacts/dora_rerun_scene.rrd` is non-empty;
- `artifacts/rerun_viewer_screenshot.png` is non-empty;
- `artifacts/rerun_viewer_recording.mp4` is non-empty;
- the log contains `visualizer received final frame`;
- the log contains `Verified: Rerun recording was generated.`.

Only `.venv/`, `.tools/`, `artifacts/`, `logs/`, `out/`, and Rerun
runtime state may be generated. No tracked source file needs to change.
