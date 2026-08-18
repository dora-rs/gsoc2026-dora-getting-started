# Asset execution guide

Keep `VERSIONS.md` and all locks unchanged. The only supported entry is
`bash tutorial.sh run`; `--run-seconds 180` is the only optional parameter. The
script owns Webots, Dora, Octos, the three roles, recording, and cleanup.

Acceptance requires 145 tests, Observer/Operator/Supervisor activity, an
activated generated strategy, switch actions, at least one completed safe
control cycle, both switches off at exit, a non-empty application video, and
final `PASS`.
