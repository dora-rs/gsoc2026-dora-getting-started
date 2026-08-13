# 参考资料

准备本教程时检查了这些来源。

| 主题 | 来源 |
| --- | --- |
| Dora 主仓库和 README | <https://github.com/dora-rs/dora> |
| Dora v1.0.0-rc.4 release | <https://github.com/dora-rs/dora/releases/tag/v1.0.0-rc.4> |
| Dora CLI 指南 | <https://dora-rs.ai/dora/operations/cli> |
| Dora Python API | <https://dora-rs.ai/dora/languages/python> |
| Dora crates.io 包 | <https://crates.io/crates/dora-cli/1.0.0-rc.4> |
| Dora PyPI 包 | <https://pypi.org/project/dora-rs/1.0.0rc4/> |
| Adora 归档与合并说明 | <https://github.com/dora-rs/adora> |
| Codex CLI | <https://learn.chatgpt.com/docs/codex/cli> |
| Codex 模型 | <https://learn.chatgpt.com/docs/models> |
| Codex 命令 | <https://learn.chatgpt.com/docs/developer-commands?surface=cli> |
| Rerun Python SDK 安装指南 | <https://rerun.io/docs/getting-started/install-rerun/python> |
| Rerun log and ingest 指南 | <https://rerun.io/docs/getting-started/data-in> |
| Rerun CLI manual | <https://rerun.io/docs/reference/cli> |
| Rerun SDK PyPI 包 | <https://pypi.org/project/rerun-sdk/> |
| Rerun GitHub 仓库 | <https://github.com/rerun-io/rerun> |
| Claude Code 概览 | <https://docs.anthropic.com/en/docs/claude-code/overview> |
| OpenClaw 仓库 | <https://github.com/openclaw/openclaw> |
| Octos 仓库 | <https://github.com/octos-org/octos> |

## 来源说明

- `adora` 仓库已经归档，并说明后续工作进入 `dora-rs/dora`，所以本书把 Dora 作为当前活跃的项目入口。
- 本教程把 Dora CLI release 压缩包固定为 `1.0.0-rc.4`，并在隔离的 Python 3.11
  环境中安装 `dora-rs==1.0.0rc4`。这样 CLI runtime 与 Python API 保持一致，也不会
  改变已有的全局安装。
- Rerun 的包信息和平台信息在准备 Rerun 场景章节时，根据官方 Rerun 文档和 PyPI `rerun-sdk` 包页面检查。
