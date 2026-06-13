# dora-rs 介绍、安装与 Hello World

| 组件 | 版本 / 环境 |
| --- | --- |
| 操作系统 | Microsoft Windows 11 Pro, build 26200, x64 |
| Dora CLI | 0.5.0 |
| dora-rs Python 包 | `dora-rs==0.5.0` |
| Python | CPython 3.11.14 via `uv` |
| uv | 0.11.17 |
| pyarrow | 24.0.0 |
| PyYAML | 6.0.3 |
| 验证示例 | `verification/week1-hello-world` |

## 目标

读完本章后，新用户应该能够说明 Dora 是什么，安装一个可复现的本地环境，并运行一个由两个节点组成的 Hello World dataflow。

这个示例刻意保持很小：

- `talker.py` 接收定时器 tick，并发送一个 Apache Arrow 字符串。
- `listener.py` 接收消息并打印。
- `dataflow.yml` 把两个节点连起来。
- `run.ps1` 创建隔离环境、安装 Dora、运行 dataflow，并检查预期输出。

## Dora 是什么

Dora 是面向机器人和 AI 应用的 dataflow 框架。一个 Dora 应用可以描述为一个有向图：节点产生输出，其他节点订阅这些输出作为输入，运行时负责在节点之间传递带类型的消息。

对入门用户来说，最重要的是这些概念：

| 概念 | 在本示例中的含义 |
| --- | --- |
| Dataflow | `dataflow.yml` 声明的完整流水线 |
| Node | 一个进程或脚本，例如 `talker.py` 或 `listener.py` |
| Input | 节点接收的命名流，例如 `greeting` |
| Output | 节点发布的命名流，例如 `greeting` |
| Timer | 内置节点来源，这里是 `dora/timer/secs/1` |
| Arrow value | Python API 使用的列式消息格式 |

## Dora 与 Adora

较早的 Dora 资料可能同时提到 `dora-rs` 和 `adora`。当前上游状态是：

- `dora-rs/dora` 是 Dora 当前活跃仓库。
- `dora-rs/adora` 已归档，并说明该 fork 已合并进 `dora-rs/dora`，作为 1.0 baseline。

本教程使用当前活跃的 Dora 包名进行安装和运行：

- CLI 包：`dora-rs-cli`
- Python API 包：`dora-rs`
- Python import 名称：`dora`

不要使用 `pip install dora`。这个包名不是 Dora robotics framework。

## 安装选择

Dora 官方资料列出了几种安装路径：

| 方式 | 适合场景 | 命令 |
| --- | --- | --- |
| Python virtual environment | Windows 上可复现的教程验证 | `pip install dora-rs-cli dora-rs` |
| Cargo | 希望从 crates.io 安装 CLI 的 Rust 开发者 | `cargo install dora-cli` |
| Windows installer | 用户级 CLI 安装 | `powershell -ExecutionPolicy ByPass -c "irm https://github.com/dora-rs/dora/releases/latest/download/dora-cli-installer.ps1 \| iex"` |
| macOS/Linux installer | 用户级 CLI 安装 | `curl --proto '=https' --tlsv1.2 -LsSf https://github.com/dora-rs/dora/releases/latest/download/dora-cli-installer.sh \| sh` |

本章采用 Python virtual environment 路径，因为它让验证过程自包含，也不会改变机器上已有的 Dora 源码构建。

## 本地验证

从教程根目录运行：

```powershell
cd verification/week1-hello-world
./run.ps1
```

脚本会执行这些步骤：

1. 查找 `uv`。
2. 如果本地还没有 `.venv`，用 CPython 3.11 创建它。
3. 根据 `requirements.txt` 安装固定版本依赖。
4. 打印 Dora 与 Python 包版本。
5. 运行 `dora run dataflow.yml --uv --stop-after 4s`。
6. 如果没有观察到 listener 输出，则失败退出。

预期成功标记：

```text
listener received: Hello from dora-rs #1 from greeting
Verified: listener output was observed.
```

## Dataflow

`dataflow.yml` 声明了两个节点。内置 timer 每秒向 `talker` 发送 tick；`talker` 发布 `greeting`；`listener` 订阅这个 greeting。

```yaml
nodes:
  - id: talker
    path: talker.py
    inputs:
      tick: dora/timer/secs/1
    outputs:
      - greeting

  - id: listener
    path: listener.py
    inputs:
      greeting: talker/greeting
```

## Talker 节点

`talker.py` 等待输入事件。每个 timer 事件都会触发一次 Arrow 消息发送。

```python
import pyarrow as pa
from dora import Node

node = Node()
count = 0

for event in node:
    if event["type"] == "INPUT":
        count += 1
        node.send_output("greeting", pa.array([f"Hello from dora-rs #{count}"]))
    elif event["type"] == "STOP":
        break
```

关键点：

- `Node()` 把 Python 脚本连接到 Dora 运行时。
- `event["type"] == "INPUT"` 表示节点收到了数据。
- `pa.array([...])` 把 Python 数据包装成 Apache Arrow。
- `send_output("greeting", ...)` 发布到 YAML 中声明的输出。

## Listener 节点

`listener.py` 等待输入消息，并把第一个 Arrow 值转成原生 Python 字符串后打印。

```python
from dora import Node

node = Node()

for event in node:
    if event["type"] == "INPUT":
        message = event["value"][0].as_py()
        print(f"listener received: {message} from {event['id']}")
    elif event["type"] == "STOP":
        break
```

listener 看到的输入 ID 是 `greeting`，因为这是 `dataflow.yml` 里的本地输入名。

## 示例输出

成功运行会包含类似这些行：

```text
listener received: Hello from dora-rs #1 from greeting
listener received: Hello from dora-rs #2 from greeting
listener received: Hello from dora-rs #3 from greeting
```

具体时间戳、进程 ID 和 daemon ID 都是机器相关信息，不会复制到公开文档中。

## 故障排查

| 现象 | 检查项 |
| --- | --- |
| 找不到 `uv` | 安装 `uv`，然后打开新的 PowerShell 会话 |
| `dora` 显示旧版本 | 运行 `Get-Command dora`，可能有另一个 Dora build 排在 `PATH` 前面 |
| listener 没有输出 | 确认 `talker` 会持续运行直到 stop signal；如果立刻退出，dataflow 可能来不及投递消息 |
| PowerShell 阻止脚本 | 在可信 checkout 中运行脚本，或使用 `Set-ExecutionPolicy -Scope Process Bypass` |

## 用 Codex CLI 完成同样任务

本节基于官方 Codex CLI 文档整理，用作操作引导。上面的 Dora 示例已经在本机验证；下面的 Codex CLI 命令需要在你自己的 Codex 会话中确认。

### Codex 官方文档链接

- CLI 概览：<https://developers.openai.com/codex/cli>
- CLI 功能：<https://developers.openai.com/codex/cli/features>
- CLI 命令行选项：<https://developers.openai.com/codex/cli/reference>
- Codex 模型：<https://developers.openai.com/codex/models>
- 配置基础：<https://developers.openai.com/codex/config-basic>
- 审批与安全：<https://developers.openai.com/codex/agent-approvals-security>
- 沙盒机制：<https://developers.openai.com/codex/concepts/sandboxing>

### 安装 Codex CLI

Windows 上可以在 PowerShell 中使用 standalone installer：

```powershell
irm https://chatgpt.com/codex/install.ps1 | iex
codex
```

如果你已经安装 Node.js，也可以使用 npm：

```powershell
npm install -g @openai/codex
codex
```

macOS 或 Linux 上，Codex CLI 文档展示的 standalone installer 是：

```bash
curl -fsSL https://chatgpt.com/codex/install.sh | sh
codex
```

第一次运行时会提示你使用 ChatGPT 账号或 API key 登录。

### 在本仓库中启动

```powershell
cd <repo>
codex
```

在可信 checkout 中进行普通交互式开发时，建议使用 workspace write 权限，并保留审批提示：

```powershell
codex --sandbox workspace-write --ask-for-approval on-request
```

然后可以让 Codex 执行：

```text
Install the latest dora-rs CLI and Python package in an isolated environment,
create a minimal talker/listener Hello World dataflow, run it locally, and
document the exact versions and verification command. Do not include secrets,
tokens, private usernames, or absolute local paths in committed docs.
```

如果希望 Codex 在会话中查找最新公开文档，可以启用 live search：

```powershell
codex --search --sandbox workspace-write --ask-for-approval on-request
```

Web search 和命令的网络访问权限是两件事。如果安装包时无法访问 PyPI 或 GitHub，说明命令网络访问可能被沙盒拦截，可以重新启动并显式允许 workspace 网络访问：

```powershell
codex --sandbox workspace-write --ask-for-approval on-request --config sandbox_workspace_write.network_access=true
```

### 选择模型

Codex 官方文档推荐大多数 Codex 任务从 `gpt-5.5` 开始，尤其适合复杂编码、调研、computer use，以及多步骤文档工作。任务较轻、并且更看重速度或成本时，可以选择 `gpt-5.4-mini`。如果账号中可用 `gpt-5.3-codex-spark`，更适合作为快速迭代模型，而不是严谨端到端验证的首选。

为单次运行指定模型：

```powershell
codex --model gpt-5.5
```

在已打开的交互会话中，可以使用：

```text
/model
```

如果希望 CLI 和 IDE 默认使用同一个模型，可以在 `~/.codex/config.toml` 中写入：

```toml
model = "gpt-5.5"
```

### 选择思考强度

思考强度控制模型在支持该能力时回答前投入多少推理。更高的思考强度可能提升复杂调试、设计和多文件修改质量，但会更慢，也会消耗更多 token。

实用建议：

- 简单安装、解释和小范围文档修改，使用 `medium` 或默认值。
- 如果要让 Codex 在一次任务中查文档、安装依赖、写代码、运行验证并更新正文，使用 `high`。
- `xhigh` 留给困难架构分析或复杂调试，前提是可以接受更长等待时间。

为单次运行指定思考强度：

```powershell
codex --model gpt-5.5 --config model_reasoning_effort='"high"'
```

或在 `~/.codex/config.toml` 中持久化：

```toml
model_reasoning_effort = "high"
```

### 设置权限

Codex 权限由两层组成：

- `sandbox_mode` 决定 Codex 执行命令时技术上能访问什么。
- `approval_policy` 决定 Codex 什么时候必须停下来请求确认。

常用本地模式：

- `read-only`：适合解释、规划，或只让 Codex 读取文件而不修改。
- `workspace-write`：适合普通教程开发；Codex 可以在当前 workspace 内编辑并运行常规命令。
- `danger-full-access`：移除沙盒边界。只建议在一次性或严格受控环境中使用。

Dora Hello World 任务推荐：

```powershell
codex --sandbox workspace-write --ask-for-approval on-request
```

只讨论不修改时：

```powershell
codex --sandbox read-only --ask-for-approval on-request
```

本机持久默认值可以这样写：

```toml
sandbox_mode = "workspace-write"
approval_policy = "on-request"

[sandbox_workspace_write]
network_access = false
```

交互会话中，可以使用 `/permissions` 随任务切换权限模式，并用 `/status` 查看当前 workspace 和权限状态。

### 实用提示

- 先让 Codex 检查仓库并总结预计修改哪些文件，再开始编辑。
- 明确要求使用隔离虚拟环境，除非你特别说明，否则不要修改全局 Python、Rust 或 Dora 安装。
- 让 Codex 运行验证脚本，并只汇报脱敏后的版本行和 Hello World listener 输出。
- 明确要求不要把 secrets、私人用户名、机器 ID、本地绝对路径、access token 写进文档。
- 最后让 Codex 给出 changed-file summary，方便快速 review。

示例 prompt：

```text
Use the current Dora documentation to install the latest dora-rs CLI and Python
package in an isolated environment. Create a minimal talker/listener Hello World
dataflow, run it locally, and update the tutorial with the exact OS and package
versions. Before editing, summarize the files you expect to change. After
running, report only sanitized version lines and listener output.
```

常用后续 prompt：

```text
Show me the files you changed and explain how the dataflow works.
```

```text
Run the verification script again and summarize only the version lines and the
listener output.
```

## 来源

- Dora repository: <https://github.com/dora-rs/dora>
- Dora installation guide: <https://dora-rs.ai/docs/guides/Installation/installing/>
- Dora Python conversation guide: <https://dora-rs.ai/docs/guides/getting-started/conversation_py/>
- Dora v0.5.0 release: <https://github.com/dora-rs/dora/releases/tag/v0.5.0>
- Adora archive notice: <https://github.com/dora-rs/adora>
- Codex CLI setup: <https://developers.openai.com/codex/cli>
- Codex CLI features: <https://developers.openai.com/codex/cli/features>
- Codex CLI options: <https://developers.openai.com/codex/cli/reference>
- Codex models: <https://developers.openai.com/codex/models>
- Codex configuration basics: <https://developers.openai.com/codex/config-basic>
- Codex approvals and security: <https://developers.openai.com/codex/agent-approvals-security>
- Codex sandboxing: <https://developers.openai.com/codex/concepts/sandboxing>
