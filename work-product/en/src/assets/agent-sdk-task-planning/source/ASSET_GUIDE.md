# Asset execution guide

Keep `VERSIONS.md` and all locks unchanged. The only supported entry is
`bash tutorial.sh run`; `--timeout-seconds 720` is the only optional parameter.
The script owns Webots, Dora Robot API, Agents SDK, verification, and cleanup.

Acceptance requires 44 tests, two named visual observations (`lit=true` then
`lit=false`), the `[DONE]` task marker, final location/arm pose `home`, two
non-empty evidence images, and final `PASS`.
