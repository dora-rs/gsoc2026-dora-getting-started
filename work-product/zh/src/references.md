# 参考资料

准备本教程时检查了这些来源。

| 主题 | 来源 |
| --- | --- |
| Dora 主仓库和 README | <https://github.com/dora-rs/dora> |
| Dora v0.5.0 release | <https://github.com/dora-rs/dora/releases/tag/v0.5.0> |
| Dora 安装指南 | <https://dora-rs.ai/docs/guides/Installation/installing/> |
| Dora Python conversation 教程 | <https://dora-rs.ai/docs/guides/getting-started/conversation_py/> |
| Dora crates.io 包 | <https://crates.io/crates/dora-cli/0.5.0> |
| Dora PyPI 包 | <https://pypi.org/project/dora-rs/0.5.0/> |
| Adora 归档与合并说明 | <https://github.com/dora-rs/adora> |
| Codex CLI 概览 | <https://developers.openai.com/codex/cli> |
| Codex CLI 功能 | <https://developers.openai.com/codex/cli/features> |
| Codex CLI 命令行选项 | <https://developers.openai.com/codex/cli/reference> |
| Codex 模型 | <https://developers.openai.com/codex/models> |
| Codex 配置基础 | <https://developers.openai.com/codex/config-basic> |
| Codex 审批与安全 | <https://developers.openai.com/codex/agent-approvals-security> |
| Codex 沙盒机制 | <https://developers.openai.com/codex/concepts/sandboxing> |

## 来源说明

- `adora` 仓库已经归档，并说明后续工作进入 `dora-rs/dora`，所以本书把 Dora 作为当前活跃的项目入口。
- Dora 官方安装页和 Dora README 当前展示的首选安装路径略有差异。本教程采用隔离 Python 虚拟环境，并固定 `dora-rs-cli==0.5.0` 与 `dora-rs==0.5.0`，因为这种方式在 Windows 上容易复现，也不会影响开发者已有的 Dora 源码构建。
