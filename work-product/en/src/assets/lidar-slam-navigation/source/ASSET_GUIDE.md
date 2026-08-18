# Asset execution guide

Use `VERSIONS.md` and the supplied image without substitutions. ROS runs with
system Python 3.10; Dora runs with `/opt/dora-venv` Python 3.11. This split is
intentional and already implemented.

The only supported entry is `bash tutorial.sh run`. Optional parameters are
`--explore-seconds 45` and `--timeout-seconds 480`. Do not invoke component
scripts, Docker, ROS, or Dora directly; the entry owns their lifecycle.

Acceptance requires a non-empty map, a `SUCCEEDED` mission result, a sent and
accepted goal, positive scan/odometry/known-cell counts, and final `PASS`.
