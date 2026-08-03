# Habitat-Sim Camera Sensor Verification

This example creates a Habitat-Sim scene with a ground plane, colored blocks,
and a Franka Panda arm. A camera link is fixed to the Panda hand in the URDF.
The script moves the arm joints, reads RGB and depth observations from the
camera link's full transform, and shows the streams in external OpenCV windows
when a desktop display is available.

The simulation treats Habitat world coordinates as Y-up. The generated GLB
scene is authored from Trimesh's Z-up source coordinates, and the script rotates
the Panda URDF root into the Y-up Habitat world before reading the wrist camera
transform.

Run:

```bash
DISPLAY=:1 bash run.sh
```

If no desktop display is available, run:

```bash
SHOW_WINDOWS=0 bash run.sh
```

The script installs micromamba locally under `.tools/`, creates a local
`habitat-camera-sensors` environment under `.mamba-root/`, and writes generated
outputs under `outputs/`.

The run script also normalizes generated `.mp4` files to H.264 with `yuv420p`,
using system `ffmpeg` with `libx264` when available. This keeps the book videos
playable in ordinary browser `<video>` elements.

Franka mesh assets are stored under `assets/franka_description/`. The source and
license are recorded in `assets/franka_description/SOURCE.txt`.

Generated files under `outputs/`, `.tools/`, `.mamba-root/`, and the generated
`assets/habitat_wrist_camera_probe.glb` are local runtime outputs. The supplied
URDF, source scripts, license note, and Franka meshes are the fixed reference
inputs.
