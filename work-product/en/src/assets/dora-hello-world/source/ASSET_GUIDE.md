# Dora Hello World asset guide

## Goal

Run the supplied talker/listener dataflow and observe at least one line
beginning with:

```text
listener received: Hello from dora-rs
```

## Single entry

Run from PowerShell on Windows 11:

```powershell
./run.ps1 -Seconds 4
```

Do not invoke pip, uv, curl, dora, Python, or an alternative script directly.
The entry script owns environment creation, installation, execution, and
acceptance.

## Immutable source files

- dataflow.yml
- talker.py
- listener.py
- requirements.txt
- run.ps1
- TUTORIAL_CONTRACT.md
- VERSIONS.md

The entry script downloads the pinned Windows Dora CLI archive from the
official RC4 release, then checks it against the published SHA-256 digest
before extraction. A checksum mismatch stops the run.
Expected generated paths are `.venv/`, `.tools/`, `logs/`, and `out/`.
No source file needs to change during reproduction.

Success requires `./run.ps1 -Seconds 4` to exit zero, print a line beginning
with `listener received: Hello from dora-rs`, and print
`Verified: listener output was observed.`.
