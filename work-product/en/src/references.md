# References

These sources were checked while preparing this tutorial.

| Topic | Source |
| --- | --- |
| Dora main repository and README | <https://github.com/dora-rs/dora> |
| Dora v1.0.0-rc.4 release | <https://github.com/dora-rs/dora/releases/tag/v1.0.0-rc.4> |
| Dora CLI guide | <https://dora-rs.ai/dora/operations/cli> |
| Dora Python API | <https://dora-rs.ai/dora/languages/python> |
| Dora crates.io package | <https://crates.io/crates/dora-cli/1.0.0-rc.4> |
| Dora PyPI package | <https://pypi.org/project/dora-rs/1.0.0rc4/> |
| Adora archive and consolidation notice | <https://github.com/dora-rs/adora> |
| Codex CLI | <https://learn.chatgpt.com/docs/codex/cli> |
| Codex models | <https://learn.chatgpt.com/docs/models> |
| Codex commands | <https://learn.chatgpt.com/docs/developer-commands?surface=cli> |
| Rerun Python SDK install guide | <https://rerun.io/docs/getting-started/install-rerun/python> |
| Rerun log and ingest guide | <https://rerun.io/docs/getting-started/data-in> |
| Rerun CLI manual | <https://rerun.io/docs/reference/cli> |
| Rerun SDK PyPI package | <https://pypi.org/project/rerun-sdk/> |
| Rerun GitHub repository | <https://github.com/rerun-io/rerun> |
| Claude Code overview | <https://docs.anthropic.com/en/docs/claude-code/overview> |
| OpenClaw repository | <https://github.com/openclaw/openclaw> |
| Octos repository | <https://github.com/octos-org/octos> |

## Source Notes

- The `adora` repository is archived and points new work to `dora-rs/dora`, so
  this book treats Dora as the active project surface.
- The tutorial pins the Dora CLI release archive to `1.0.0-rc.4` and installs
  `dora-rs==1.0.0rc4` in an isolated Python 3.11 environment. This keeps the
  command-line runtime and Python API aligned without changing an existing
  global installation.
- Rerun package and platform details were checked against official Rerun
  documentation and the PyPI `rerun-sdk` package page while preparing the Rerun
  scene chapter.
