# dora-rs Introduction, Installation, and Hello World

| Component | Version / Environment |
| --- | --- |
| Operating system | Microsoft Windows 11 Pro, build 26200, x64 |
| Dora CLI | 0.5.0 |
| dora-rs Python package | `dora-rs==0.5.0` |
| Python | CPython 3.11.14 via `uv` |
| uv | 0.11.17 |
| pyarrow | 24.0.0 |
| PyYAML | 6.0.3 |
| Verification example | `verification/week1-hello-world` |

## Goal

By the end of this chapter, a new user can explain what Dora is, install a
reproducible local environment, and run a two-node Hello World dataflow.

The example is intentionally small:

- `talker.py` receives timer ticks and sends an Apache Arrow string.
- `listener.py` receives the message and prints it.
- `dataflow.yml` wires the nodes together.
- `run.ps1` creates an isolated environment, installs Dora, runs the dataflow,
  and checks the expected output.

## What Dora Is

Dora is a dataflow framework for robotics and AI applications. A Dora application
is described as a directed graph: nodes produce outputs, other nodes subscribe to
those outputs as inputs, and the runtime moves typed messages between them.

For beginners, the most important pieces are:

| Concept | Meaning in this example |
| --- | --- |
| Dataflow | The complete pipeline declared in `dataflow.yml` |
| Node | One process or script, such as `talker.py` or `listener.py` |
| Input | A named stream a node receives, such as `greeting` |
| Output | A named stream a node publishes, such as `greeting` |
| Timer | A built-in node source, here `dora/timer/secs/1` |
| Arrow value | The columnar message format used by the Python API |

## Dora and Adora

Older Dora materials may mention both `dora-rs` and `adora`. The current
upstream state is:

- `dora-rs/dora` is the active repository for Dora.
- `dora-rs/adora` is archived and says the fork was consolidated into
  `dora-rs/dora` as the 1.0 baseline.

For this tutorial, install and run the current Dora toolchain from the active Dora
package names:

- CLI package: `dora-rs-cli`
- Python API package: `dora-rs`
- Python import name: `dora`

Avoid `pip install dora`; that package name does not refer to the Dora robotics
framework.

## Installation Choices

Official Dora materials list several installation paths:

| Method | Best for | Command |
| --- | --- | --- |
| Python virtual environment | Reproducible tutorial work on Windows | `pip install dora-rs-cli dora-rs` |
| Cargo | Rust developers who want the CLI from crates.io | `cargo install dora-cli` |
| Windows installer | User-level CLI install | `powershell -ExecutionPolicy ByPass -c "irm https://github.com/dora-rs/dora/releases/latest/download/dora-cli-installer.ps1 \| iex"` |
| macOS/Linux installer | User-level CLI install | `curl --proto '=https' --tlsv1.2 -LsSf https://github.com/dora-rs/dora/releases/latest/download/dora-cli-installer.sh \| sh` |

This chapter uses the Python virtual environment route because it keeps the
verification self-contained and avoids changing any existing Dora source build on
the machine.

## Local Verification Setup

From the tutorial root:

```powershell
cd verification/week1-hello-world
./run.ps1
```

The script performs these steps:

1. Finds `uv`.
2. Creates `.venv` with CPython 3.11 if it does not already exist.
3. Installs pinned packages from `requirements.txt`.
4. Prints Dora and Python package versions.
5. Runs `dora run dataflow.yml --uv --stop-after 4s`.
6. Fails if the listener output is not present.

Expected success marker:

```text
listener received: Hello from dora-rs #1 from greeting
Verified: listener output was observed.
```

## Dataflow

`dataflow.yml` declares two nodes. The built-in timer sends a tick every second
to `talker`; `talker` publishes a `greeting`; `listener` subscribes to that
greeting.

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

## Talker Node

`talker.py` waits for input events. Each timer event triggers one Arrow message.

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

Key points:

- `Node()` connects the Python script to the Dora runtime.
- `event["type"] == "INPUT"` means the node received data.
- `pa.array([...])` wraps Python data in Apache Arrow.
- `send_output("greeting", ...)` publishes to the output declared in YAML.

## Listener Node

`listener.py` waits for input messages and prints the first Arrow value as a
native Python string.

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

The listener sees the input ID `greeting`, because that is the local input name
in `dataflow.yml`.

## Example Output

A successful run includes lines like:

```text
listener received: Hello from dora-rs #1 from greeting
listener received: Hello from dora-rs #2 from greeting
listener received: Hello from dora-rs #3 from greeting
```

The exact timestamps, process IDs, and daemon IDs are machine-specific and are
not copied into public documentation.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| `uv` is not found | Install `uv`, then open a new PowerShell session |
| `dora` shows an older version | Run `Get-Command dora`; another Dora build may be earlier in `PATH` |
| Listener output is missing | Confirm `talker` keeps running until the stop signal; exiting immediately can stop the dataflow before delivery |
| PowerShell blocks scripts | Run the script from a trusted checkout, or use a session policy such as `Set-ExecutionPolicy -Scope Process Bypass` |

## Using Codex CLI for the Same Task

This section summarizes the official Codex CLI documentation and is intended as
a guided workflow. The Dora verification above was run locally; the Codex CLI
commands below should be checked in your own Codex session.

### Official Codex Links

- CLI overview: <https://developers.openai.com/codex/cli>
- CLI features: <https://developers.openai.com/codex/cli/features>
- CLI command reference: <https://developers.openai.com/codex/cli/reference>
- Models in Codex: <https://developers.openai.com/codex/models>
- Configuration basics: <https://developers.openai.com/codex/config-basic>
- Approvals and security: <https://developers.openai.com/codex/agent-approvals-security>
- Sandboxing: <https://developers.openai.com/codex/concepts/sandboxing>

### Install Codex CLI

On Windows, use the standalone installer from PowerShell:

```powershell
irm https://chatgpt.com/codex/install.ps1 | iex
codex
```

If you prefer npm and already have Node.js installed, use:

```powershell
npm install -g @openai/codex
codex
```

On macOS or Linux, the standalone installer shown in the Codex CLI docs is:

```bash
curl -fsSL https://chatgpt.com/codex/install.sh | sh
codex
```

The first run prompts you to sign in with a ChatGPT account or an API key.

### Start in This Repository

```powershell
cd <repo>
codex
```

For a normal interactive run in a trusted checkout, use workspace write access
with approval prompts:

```powershell
codex --sandbox workspace-write --ask-for-approval on-request
```

Then ask Codex:

```text
Install the latest dora-rs CLI and Python package in an isolated environment,
create a minimal talker/listener Hello World dataflow, run it locally, and
document the exact versions and verification command. Do not include secrets,
tokens, private usernames, or absolute local paths in committed docs.
```

If you want Codex to look up the latest public documentation during the session,
start with live search enabled:

```powershell
codex --search --sandbox workspace-write --ask-for-approval on-request
```

Web search and command network access are separate controls. If package
installation cannot reach PyPI or GitHub because command network access is
blocked, restart with explicit workspace network access:

```powershell
codex --sandbox workspace-write --ask-for-approval on-request --config sandbox_workspace_write.network_access=true
```

### Choose a Model

Official Codex documentation recommends `gpt-5.5` for most Codex tasks,
especially complex coding, research, computer use, and multi-step documentation
work. Use `gpt-5.4-mini` when the task is lighter and speed or cost matters
more than maximum reasoning depth. If your account exposes
`gpt-5.3-codex-spark`, treat it as a fast iteration model rather than the first
choice for careful end-to-end verification.

Choose a model for one run:

```powershell
codex --model gpt-5.5
```

Inside an active session, use:

```text
/model
```

To make the choice persistent for local CLI and IDE use, add this to
`~/.codex/config.toml`:

```toml
model = "gpt-5.5"
```

### Choose Reasoning Effort

Reasoning effort controls how long Codex thinks before responding when the
selected model supports it. Higher effort can improve quality for complex
debugging, design, and multi-file edits, but it is slower and uses more tokens.

Practical defaults:

- Use `medium` or the built-in default for straightforward installation and
  small documentation edits.
- Use `high` for this tutorial workflow if Codex must inspect docs, install
  packages, write code, run verification, and update prose in one pass.
- Use `xhigh` only for difficult architecture or debugging work where latency is
  acceptable.

Choose a reasoning effort for one run:

```powershell
codex --model gpt-5.5 --config model_reasoning_effort='"high"'
```

Or persist it in `~/.codex/config.toml`:

```toml
model_reasoning_effort = "high"
```

### Set Permissions

Codex permissions have two layers:

- `sandbox_mode` defines what Codex commands can technically access.
- `approval_policy` defines when Codex must stop and ask before crossing that
  boundary.

Useful local modes:

- `read-only`: best for explanation, planning, or asking Codex to inspect files
  without editing.
- `workspace-write`: best for normal tutorial work; Codex can edit and run
  routine commands inside the current workspace.
- `danger-full-access`: removes the sandbox boundary. Use it only in a
  disposable or tightly controlled environment.

Recommended mode for the Dora Hello World task:

```powershell
codex --sandbox workspace-write --ask-for-approval on-request
```

Read-only discussion mode:

```powershell
codex --sandbox read-only --ask-for-approval on-request
```

Persistent local defaults:

```toml
sandbox_mode = "workspace-write"
approval_policy = "on-request"

[sandbox_workspace_write]
network_access = false
```

During an interactive session, use `/permissions` to switch modes as the task
changes, and `/status` to inspect the current workspace and permission state.

### Practical Prompt Tips

- Ask Codex to inspect the repository and summarize the intended file changes
  before editing.
- Tell Codex to use an isolated virtual environment and avoid modifying global
  Python, Rust, or Dora installations unless you explicitly want that.
- Ask it to run the verification script and report only sanitized version lines
  and the Hello World listener output.
- Ask it to keep secrets, private usernames, machine IDs, absolute local paths,
  and access tokens out of committed documentation.
- Ask for a final changed-file summary so you can review the work quickly.

Example prompt:

```text
Use the current Dora documentation to install the latest dora-rs CLI and Python
package in an isolated environment. Create a minimal talker/listener Hello World
dataflow, run it locally, and update the tutorial with the exact OS and package
versions. Before editing, summarize the files you expect to change. After
running, report only sanitized version lines and listener output.
```

Useful follow-up prompts:

```text
Show me the files you changed and explain how the dataflow works.
```

```text
Run the verification script again and summarize only the version lines and the
listener output.
```

## Sources

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
