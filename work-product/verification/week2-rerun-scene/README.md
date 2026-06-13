# Rerun Scene Verification

This example runs a small Dora dataflow that sends scene state into a Rerun
visualizer. The visualizer writes `artifacts/dora_rerun_scene.rrd` and uses
reusable glTF assets for the robot and car. On a desktop session, `run.sh` also
captures a Rerun Viewer screenshot and a short recording.

```bash
./run.sh
```

Generated files under `artifacts/`, generated models under `models/`, and
runtime logs under `logs/` are local verification outputs. Curated Viewer media
is copied into the book's `src/assets/` directory.
