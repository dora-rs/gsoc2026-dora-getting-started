# Verification

This folder stores runnable examples, scripts, and sanitized verification notes
for the book chapters.

Rules:

- Keep each chapter's code in a separate folder.
- Use isolated environments such as `.venv`.
- Commit source code, scripts, requirements, and sanitized notes.
- Do not commit local virtual environments, raw runtime logs, tokens, or private
  absolute paths.

Current examples:

| Chapter | Folder | Purpose |
| --- | --- | --- |
| Dora Hello World | `dora-hello-world` | Install Dora 1.0.0-rc.4 in isolated tooling and run a two-node dataflow |
