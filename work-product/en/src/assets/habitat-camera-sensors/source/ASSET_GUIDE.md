# Habitat camera sensors asset guide

Use the supplied GLB, URDF, environment.yml, scene script, and run.sh
unchanged. The only entry command is:

```bash
DISPLAY=:1 SHOW_WINDOWS=1 bash run.sh
```

Do not invoke micromamba, Python, ffmpeg, or camera_sensor_scene.py as an
alternative launch path. The entry owns environment creation, execution,
browser-video normalization, and acceptance.

Success requires these non-empty outputs:

- outputs/screenshots/habitat_overview.png
- outputs/screenshots/external_rgb_window.png
- outputs/screenshots/external_depth_window.png
- outputs/videos/external_rgb_stream.mp4
- outputs/videos/external_depth_stream.mp4
- outputs/videos/external_rgb_depth_side_by_side.mp4
- outputs/videos/habitat_overview.mp4

The log must print all three `Verified:` markers from run.sh. Only
`.tools/`, `.mamba-root/`, and `outputs/` may be generated.
