# Asset execution guide

Keep all versions from `VERSIONS.md`; use system Python 3.10 for ROS and the
supplied Python 3.11 runtime for Dora. The only supported entry is
`bash tutorial.sh run`. `--timeout-seconds 600` is the only optional parameter.
Do not invoke Docker, Webots, Dora, or component scripts directly.

Acceptance requires 26 focused tests, a `SUCCEEDED` mission, an ON observation,
an OFF verification, a successful return home, and final `PASS`.
