# dora-rs Introduction, Installation, and Hello World

## Version Information

| Component | Version / Environment |
| --- | --- |
| Operating system | Microsoft Windows 11 Pro, build 26200, x64 |
| Dora CLI | 1.0.0-rc.4 |
| dora-rs Python package | `dora-rs==1.0.0rc4` |
| Python | CPython 3.11.14 via `uv` |
| uv | 0.11.17 |
| pyarrow | 24.0.0 |
| PyYAML | 6.0.3 |

## Downloads

- [Verified Dora Hello World project](../assets/dora-hello-world/dora-hello-world-reference.zip)

## Goal

By the end of this chapter, a new user can explain what Dora is, install a
reproducible local environment, and run a two-node Hello World dataflow.

The example is intentionally small:

- `talker.py` receives timer ticks and sends an Apache Arrow string.
- `listener.py` receives the message and prints it.
- `dataflow.yml` wires the nodes together.
- `run.ps1` creates an isolated environment, installs Dora, runs the dataflow,
  and checks the expected output.

## Choose a Build Route

<div class="prompt-route prompt-route--create">
  <span class="prompt-route__label">Create route</span>
  <strong>Build the smallest Dora application from scratch</strong>
  <p>Use this when you want the assistant to create and explain every file.</p>
</div>

```text
Create a minimal Dora 1.0.0-rc.4 Hello World project without using an existing
example. Target CPython 3.11 and dora-rs==1.0.0rc4. Create talker.py,
listener.py, dataflow.yml, pinned requirements, and one run script for this OS.
The talker must publish an Apache Arrow string after timer input; the listener
must print it. Keep the environment inside the project, verify the official CLI
archive checksum, and do not alter a global Dora installation.

Before writing files, show the dataflow and file plan. After implementation,
run it for four seconds and report the observed listener line, exact versions,
generated paths, and source diff. Do not claim success unless the listener
output is present in the runtime log.
```

<div class="prompt-route prompt-route--reproduce">
  <span class="prompt-route__label">Reproduce route</span>
  <strong>Run the verified project as supplied</strong>
  <p>Use this for the fastest and most reliable first Dora run.</p>
</div>

```text
Extract the supplied Dora Hello World project. Read VERSIONS.md,
TUTORIAL_CONTRACT.md, ASSET_GUIDE.md, and READER_PROMPT.md before acting.
Treat the source and pinned versions as immutable. Report the single supported
entry, generated paths, and exact acceptance marker, then run only that entry.
Do not install or launch components separately. Verify the runtime marker and
git status; if either is missing, report FAIL and the exact stage.
```

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

- CLI command: `dora`, installed from the official release, installer, or `dora-cli` crate
- Python API package: `dora-rs`
- Python import name: `dora`

Avoid `pip install dora`; that package name does not refer to the Dora robotics
framework.

## Installation Choices

Official Dora materials list several installation paths:

| Method | Best for | Command |
| --- | --- | --- |
| Release archive + Python virtual environment | Reproducible, pinned tutorial work | Download Dora CLI `1.0.0-rc.4`, then `pip install dora-rs==1.0.0rc4` |
| Cargo | Rust developers who want the CLI from crates.io | `cargo install dora-cli` |
| Windows installer | User-level CLI install | `powershell -ExecutionPolicy ByPass -c "irm https://github.com/dora-rs/dora/releases/latest/download/dora-cli-installer.ps1 \| iex"` |
| macOS/Linux installer | User-level CLI install | `curl --proto '=https' --tlsv1.2 -LsSf https://github.com/dora-rs/dora/releases/latest/download/dora-cli-installer.sh \| sh` |

This chapter uses the pinned release archive together with a Python virtual
environment. The CLI and Python API therefore use the same Dora release without
changing an existing global installation.

## Local Verification Setup

From the tutorial root:

```powershell
cd verification/dora-hello-world
./run.ps1
```

The script performs these steps:

1. Finds `uv`.
2. Creates `.venv` with CPython 3.11 if it does not already exist.
3. Downloads and verifies the Dora CLI `1.0.0-rc.4` archive.
4. Installs pinned packages from `requirements.txt`.
5. Prints Dora and Python package versions.
6. Runs `dora run dataflow.yml --uv --stop-after 4s`.
7. Fails if the listener output is not present.

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

## Continue with a Coding Assistant

The route prompts near the beginning of this chapter work with any capable coding
assistant. Before granting file or shell access, read
[Preparation: LLMs, Agents, and Coding Assistants](preparation-llms-agents-coding-assistants.md)
to choose a model, set reasoning effort and permissions, and test the connection.
Then return here and use either the create route or the verified-asset route.
## Sources

- Dora repository: <https://github.com/dora-rs/dora>
- Dora CLI guide: <https://dora-rs.ai/dora/operations/cli>
- Dora Python API: <https://dora-rs.ai/dora/languages/python>
- Dora v1.0.0-rc.4 release: <https://github.com/dora-rs/dora/releases/tag/v1.0.0-rc.4>
- Adora archive notice: <https://github.com/dora-rs/adora>

## Next Step

The preparation chapter explains LLMs, Agents, coding assistants, and the
recommended OctosCode and DeepSeek setup before the tutorial moves into 3D
visualization.
