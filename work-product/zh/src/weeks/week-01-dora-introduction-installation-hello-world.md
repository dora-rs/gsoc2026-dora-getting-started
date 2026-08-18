# dora-rs 介绍、安装与 Hello World

## 版本信息

| 组件 | 版本 / 环境 |
| --- | --- |
| 操作系统 | Microsoft Windows 11 Pro, build 26200, x64 |
| Dora CLI | 1.0.0-rc.4 |
| dora-rs Python 包 | `dora-rs==1.0.0rc4` |
| Python | CPython 3.11.14 via `uv` |
| uv | 0.11.17 |
| pyarrow | 24.0.0 |
| PyYAML | 6.0.3 |

## 下载

- [已验证的 Dora Hello World 工程](../assets/dora-hello-world/dora-hello-world-reference.zip)

## 目标

读完本章后，新用户应该能够说明 Dora 是什么，安装一个可复现的本地环境，并运行一个由两个节点组成的 Hello World dataflow。

这个示例刻意保持很小：

- `talker.py` 接收定时器 tick，并发送一个 Apache Arrow 字符串。
- `listener.py` 接收消息并打印。
- `dataflow.yml` 把两个节点连起来。
- `run.ps1` 创建隔离环境、安装 Dora、运行 dataflow，并检查预期输出。

## 选择实现路线

<div class="prompt-route prompt-route--create">
  <span class="prompt-route__label">创造路线</span>
  <strong>从零创建最小 Dora 应用</strong>
  <p>适合希望让编程助手创建并解释每个文件的读者。</p>
</div>

```text
不要使用现有示例，从零创建一个最小的 Dora 1.0.0-rc.4 Hello World 工程。
使用 CPython 3.11 和 dora-rs==1.0.0rc4。创建 talker.py、listener.py、
dataflow.yml、固定版本的 requirements，以及适合当前操作系统的唯一运行脚本。
talker 必须在收到 timer input 后发布 Apache Arrow 字符串，listener 必须打印它。
环境只能创建在工程目录中；校验官方 CLI 压缩包的 checksum，不修改全局 Dora。

写文件前先给出 dataflow 和文件计划。实现后运行四秒，报告实际观察到的 listener
输出、准确版本、生成目录和源码 diff。运行日志中没有 listener 输出时不能声称成功。
```

<div class="prompt-route prompt-route--reproduce">
  <span class="prompt-route__label">复现路线</span>
  <strong>按原样运行已验证工程</strong>
  <p>适合最快、最可靠地完成第一次 Dora 运行。</p>
</div>

```text
解压提供的 Dora Hello World 工程。操作前读取 VERSIONS.md、
TUTORIAL_CONTRACT.md、ASSET_GUIDE.md 和 READER_PROMPT.md。源码和固定版本不可修改。
先报告唯一入口、生成目录和准确验收标记，再只运行该入口。不要单独安装或启动组件。
检查运行时标记和 git status；任一条件缺失都要报告 FAIL 和准确阶段。
```

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

- CLI 命令：`dora`，通过官方 release、安装脚本或 `dora-cli` crate 安装
- Python API 包：`dora-rs`
- Python import 名称：`dora`

不要使用 `pip install dora`。这个包名不是 Dora robotics framework。

## 安装选择

Dora 官方资料列出了几种安装路径：

| 方式 | 适合场景 | 命令 |
| --- | --- | --- |
| Release 压缩包 + Python virtual environment | 固定版本、可复现的教程验证 | 下载 Dora CLI `1.0.0-rc.4`，再运行 `pip install dora-rs==1.0.0rc4` |
| Cargo | 希望从 crates.io 安装 CLI 的 Rust 开发者 | `cargo install dora-cli` |
| Windows installer | 用户级 CLI 安装 | `powershell -ExecutionPolicy ByPass -c "irm https://github.com/dora-rs/dora/releases/latest/download/dora-cli-installer.ps1 \| iex"` |
| macOS/Linux installer | 用户级 CLI 安装 | `curl --proto '=https' --tlsv1.2 -LsSf https://github.com/dora-rs/dora/releases/latest/download/dora-cli-installer.sh \| sh` |

本章组合使用固定版本的 release 压缩包与 Python virtual environment，让 CLI 和
Python API 对应同一个 Dora release，同时不改变机器上已有的全局安装。

## 本地验证

从教程根目录运行：

```powershell
cd verification/dora-hello-world
./run.ps1
```

脚本会执行这些步骤：

1. 查找 `uv`。
2. 如果本地还没有 `.venv`，用 CPython 3.11 创建它。
3. 下载并校验 Dora CLI `1.0.0-rc.4` 压缩包。
4. 根据 `requirements.txt` 安装固定版本依赖。
5. 打印 Dora 与 Python 包版本。
6. 运行 `dora run dataflow.yml --uv --stop-after 4s`。
7. 如果没有观察到 listener 输出，则失败退出。

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

## 使用编程助手继续

本章开头的两种路线提示词可以交给任意能力合适的编程助手。如果需要更换模型、思考
强度、权限或 Provider 连接，请回看
[准备工作：LLM、Agent 与编程助手](preparation-llms-agents-coding-assistants.md)。

## 来源

- Dora repository: <https://github.com/dora-rs/dora>
- Dora CLI guide: <https://dora-rs.ai/dora/operations/cli>
- Dora Python API: <https://dora-rs.ai/dora/languages/python>
- Dora v1.0.0-rc.4 release: <https://github.com/dora-rs/dora/releases/tag/v1.0.0-rc.4>
- Adora archive notice: <https://github.com/dora-rs/adora>

## 下一步

下一章会在当前 Dora 环境中加入 Rerun，并创建第一个静态 3D 场景。
