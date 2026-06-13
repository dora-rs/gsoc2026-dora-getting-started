# References

These sources were checked while preparing this tutorial.

| Topic | Source |
| --- | --- |
| Dora main repository and README | <https://github.com/dora-rs/dora> |
| Dora v0.5.0 release | <https://github.com/dora-rs/dora/releases/tag/v0.5.0> |
| Dora installation guide | <https://dora-rs.ai/docs/guides/Installation/installing/> |
| Dora Python conversation tutorial | <https://dora-rs.ai/docs/guides/getting-started/conversation_py/> |
| Dora crates.io package | <https://crates.io/crates/dora-cli/0.5.0> |
| Dora PyPI package | <https://pypi.org/project/dora-rs/0.5.0/> |
| Adora archive and consolidation notice | <https://github.com/dora-rs/adora> |
| Codex CLI overview | <https://developers.openai.com/codex/cli> |
| Codex CLI features | <https://developers.openai.com/codex/cli/features> |
| Codex CLI command line options | <https://developers.openai.com/codex/cli/reference> |
| Codex models | <https://developers.openai.com/codex/models> |
| Codex configuration basics | <https://developers.openai.com/codex/config-basic> |
| Codex approvals and security | <https://developers.openai.com/codex/agent-approvals-security> |
| Codex sandboxing | <https://developers.openai.com/codex/concepts/sandboxing> |

## Source Notes

- The `adora` repository is archived and points new work to `dora-rs/dora`, so
  this book treats Dora as the active project surface.
- The official Dora installation page and the Dora README currently expose
  slightly different first-choice installation paths. This tutorial uses an isolated
  Python virtual environment with `dora-rs-cli==0.5.0` and `dora-rs==0.5.0`
  because it is easy to reproduce on Windows and does not disturb a developer's
  existing source checkout.
