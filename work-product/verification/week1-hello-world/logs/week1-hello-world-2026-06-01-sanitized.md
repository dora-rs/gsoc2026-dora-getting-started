# Week 1 Verification Log

Date: 2026-06-01, Asia/Shanghai

Environment:

- OS: Microsoft Windows 11 Pro, build 26200, x64
- Python: CPython 3.11.14
- Dora CLI: 0.5.0
- `dora-rs` Python package: 0.5.0
- `pyarrow`: 24.0.0
- `PyYAML`: 6.0.3

Command:

```powershell
cd <repo>\work-product\verification\week1-hello-world
./run.ps1
```

Sanitized output excerpt:

```text
== Environment ==
Example root: <repo>\work-product\verification\week1-hello-world
dora-cli 0.5.0
dora-message: 0.8.0
python 3.11.14
dora-rs python package 0.5.0
pyarrow 24.0.0
pyyaml 6.0.3
== Running dataflow for 4s ==
listener received: Hello from dora-rs #1 from greeting
listener received: Hello from dora-rs #2 from greeting
listener received: Hello from dora-rs #3 from greeting
listener received: Hello from dora-rs #4 from greeting
Verified: listener output was observed.
```

Privacy note: absolute local paths, process IDs, daemon IDs, and timestamps were
removed from this committed log.
