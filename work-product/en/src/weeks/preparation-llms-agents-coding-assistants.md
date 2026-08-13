# Preparation: LLMs, Agents, and Coding Assistants

## Version Information

| Component | Version or Interface Used Here |
| --- | --- |
| OctosCode | 0.3.0 |
| DeepSeek | DeepSeek V4 Pro 0813 through the `deepseek-v4-pro` API alias |
| API style | OpenAI-compatible Chat Completions |
| Verified desktop environment | Ubuntu 24.04 LTS, x86_64 |

Model catalogs, prices, and assistant releases change quickly. Treat the tables
below as a practical starting order for this tutorial, not as a permanent global
leaderboard. Check the linked documentation before creating a paid account.

## What an LLM Is

A large language model, or LLM, predicts and generates text, code, and structured
data from the context you provide. It can explain an error or propose an
implementation, but the model alone does not open files, run a simulator, or
verify a program. Those actions come from the application and tools around it.

There are two common ways to use an LLM:

| Interface | Best For | What You Manage |
| --- | --- | --- |
| Chat | Questions, exploration, prompt drafting, and manual review | Copying context and applying the answer yourself |
| API | Repeatable application logic, structured output, tool calls, and automation | Credentials, requests, retries, costs, and result validation |

Chat is the quickest way to learn. An API is the right boundary when Dora nodes
or another program must call the model and consume a predictable result.

## Five Mainstream LLM Options

The order favors general capability, coding and tool use, documentation, and
availability for the projects in this book.

| Order | Provider | Why Consider It | Official Documentation |
| --- | --- | --- | --- |
| 1 | OpenAI | Strong general, coding, multimodal, structured-output, and tool ecosystem | [Model documentation](https://developers.openai.com/api/docs/models) |
| 2 | Anthropic Claude | Strong coding workflows, long-context work, and agent-oriented development | [Claude Platform docs](https://platform.claude.com/docs/en/intro) |
| 3 | DeepSeek | Competitive coding and reasoning with attractive API economics; the recommended value option here | [API quick start](https://api-docs.deepseek.com/) |
| 4 | Google Gemini | Broad multimodal support, long context, and a mature Google developer ecosystem | [Gemini API docs](https://ai.google.dev/gemini-api/docs) |
| 5 | xAI Grok | A mainstream API option with reasoning, tool, and realtime-oriented capabilities | [xAI docs](https://docs.x.ai/overview) |

DeepSeek is third rather than first because cost is only one part of a reliable
development workflow. Independent NIST CAISI testing found DeepSeek V4 Pro more
cost efficient than a similarly capable reference model on five of seven
compared benchmarks, while also finding a capability gap to the leading frontier
models. That balance is why it is the value recommendation, not an unconditional
best-model claim. Compare the [NIST CAISI evaluation](https://www.nist.gov/news-events/news/2026/05/caisi-evaluation-deepseek-v4-pro),
the live [Artificial Analysis model page](https://artificialanalysis.ai/models/deepseek-v4-pro),
and [DeepSeek's current pricing](https://api-docs.deepseek.com/quick_start/pricing/)
before choosing.

## Agents and Assistant Applications

An **Agent** wraps an LLM in a loop: understand a goal, select a tool, observe the
result, update state, and decide what to do next. A **coding assistant** is the
application you interact with. It packages an Agent runtime into a terminal,
IDE, desktop app, or web interface and adds file access, shell tools, diffs,
permissions, sessions, and review controls.

<div class="architecture-flow" role="img" aria-label="A user task enters a coding assistant, which manages an agent loop, calls an LLM, and uses approved tools in the workspace">
  <div class="architecture-node"><strong>Your task</strong><small>Goal and acceptance conditions</small></div>
  <div class="architecture-arrow" aria-hidden="true">&rarr;</div>
  <div class="architecture-node"><strong>Assistant app</strong><small>Terminal, IDE, app, or web UI</small></div>
  <div class="architecture-arrow" aria-hidden="true">&rarr;</div>
  <div class="architecture-node"><strong>Agent loop</strong><small>Plan, act, observe, verify</small></div>
  <div class="architecture-arrow" aria-hidden="true">&rarr;</div>
  <div class="architecture-node"><strong>LLM</strong><small>Reasoning and generation</small></div>
  <div class="architecture-arrow" aria-hidden="true">&rarr;</div>
  <div class="architecture-node"><strong>Tools</strong><small>Files, shell, tests, and web</small></div>
</div>

The model supplies much of the reasoning ability; the assistant determines how
context is assembled, which tools exist, how permissions are enforced, and how
results return to the model. Changing either layer can change the outcome.

## Five Mainstream Coding Assistants

This is again a tutorial-oriented recommendation order, not an independent
benchmark ranking.

| Order | Assistant | Practical Strength | Official Documentation |
| --- | --- | --- | --- |
| 1 | Codex CLI | Mature repository workflow, configurable models and reasoning, approvals, sandboxing, and broad tool integration | [Codex CLI docs](https://learn.chatgpt.com/docs/codex/cli) |
| 2 | Claude Code | Strong terminal workflow for codebase exploration, implementation, testing, and long-running tasks | [Claude Code docs](https://code.claude.com/docs/en/overview) |
| 3 | OctosCode | Fast terminal-native client, broad provider choice, model and thinking controls, permissions, diffs, tasks, sessions, loops, and multi-Agent views | [OctosCode repository and guide](https://github.com/octos-org/octoscode) |
| 4 | Gemini CLI | Open-source terminal Agent integrated with Gemini and Google's developer tools | [Gemini CLI repository](https://github.com/google-gemini/gemini-cli) |
| 5 | OpenCode | Open-source terminal and desktop coding Agent with multiple provider integrations | [OpenCode docs](https://opencode.ai/docs/) |

OctosCode is third because it combines a lightweight terminal workflow with a
wide control surface: provider and model selection, reasoning effort,
read-only/workspace/full-access modes, tool approvals, background tasks,
resume/rewind, loops, goals, reviews, and Agent views. Its model-independent
design also lets this tutorial use DeepSeek directly. “Performance” here means
workflow responsiveness and access to a capable selected model; OctosCode does
not make a weak model intrinsically smarter.

## The Three Controls to Set First

Regardless of the assistant, inspect these controls before asking it to edit a
repository:

- **Model:** use a capable coding model for multi-file implementation and a
  faster model for short questions. In OctosCode use `/model`.
- **Reasoning effort:** start with the default or `medium`; use `high` for
  architecture, difficult debugging, or a full build-and-verify task. In
  OctosCode use `/thinking`.
- **Permissions:** use read-only for inspection and workspace-write for normal
  implementation. Full host access belongs only in an isolated, trusted
  environment. In OctosCode use `/permissions`.

Codex exposes the same ideas through `/model`, `/permissions`, CLI options, and
its configuration file. Other assistants use different names, so follow their
official security documentation rather than copying flags between products.

## Install OctosCode

Create a [DeepSeek platform account](https://platform.deepseek.com/), add API
credit if required, and create a key on the
[API keys page](https://platform.deepseek.com/api_keys). Never put the key in a
prompt, source file, screenshot, shell history, or commit.

On macOS or Linux, use the official prebuilt installer:

```bash
curl --proto '=https' --tlsv1.2 -LsSf \
  https://github.com/octos-org/octoscode/releases/latest/download/octoscode-installer.sh | sh
source "$HOME/.cargo/env"
octoscode --version
```

On Windows, run the official PowerShell installer:

```powershell
powershell -ExecutionPolicy Bypass -c "irm https://github.com/octos-org/octoscode/releases/latest/download/octoscode-installer.ps1 | iex"
octoscode --version
```

If Node.js is already available, the official npm package is another option:

```bash
npm install -g @octos-org/octoscode
```

The first plain `octoscode` launch provisions the matching Octos server when it
is not already installed. The following recording shows the isolated Linux
installation; only the terminal application window is captured.

<video class="terminal-demo-video" controls preload="metadata" poster="../assets/ai-assistant-preparation/octoscode-install.png">
  <source src="../assets/ai-assistant-preparation/octoscode-install.mp4" type="video/mp4">
  Your browser does not support embedded video.
</video>

![OctosCode installation command and version check](../assets/ai-assistant-preparation/octoscode-install.png)

## Connect DeepSeek V4 Pro 0813

Open the project directory and launch the assistant:

```bash
cd <your-project>
octoscode
```

In the onboarding wizard, create a local profile and configure:

| Field | Value |
| --- | --- |
| Provider family | DeepSeek |
| Model | `deepseek-v4-pro` |
| Route label | DeepSeek Official |
| Base URL | `https://api.deepseek.com` |
| API type | OpenAI compatible |
| API key environment name | `DEEPSEEK_API_KEY` |

Enter the key in the protected provider field, run **Test provider**, and save
the profile. OctosCode masks keys in its UI and snapshots. The API alias remains
`deepseek-v4-pro`; the validated backend for this tutorial reported the 0813
revision.

Run a minimal test that cannot modify the workspace:

```text
Do not run tools or modify files. Reply exactly with: CONNECTION OK
```

Then inspect `/status`. The model should be `deepseek-v4-pro`, the turn should
finish without a tool call, and the reply should contain `CONNECTION OK`.

<video class="terminal-demo-video" controls preload="metadata" poster="../assets/ai-assistant-preparation/octoscode-deepseek-connection.png">
  <source src="../assets/ai-assistant-preparation/octoscode-deepseek-connection.mp4" type="video/mp4">
  Your browser does not support embedded video.
</video>

![OctosCode connected to deepseek-v4-pro and returned the expected marker](../assets/ai-assistant-preparation/octoscode-deepseek-connection.png)

## Use the Assistant with This Book

For the reliable reproduce route, download the chapter asset and start with this
instruction:

```text
Inspect VERSIONS.md, TUTORIAL_CONTRACT.md, ASSET_GUIDE.md, and READER_PROMPT.md.
Do not regenerate the project or change pinned versions. Run only the documented
entry command first, compare its acceptance markers with the contract, and do
not claim success until the command, tests, and final status all pass. Keep API
keys, usernames, hostnames, and absolute paths out of files and output.
```

For the create route, the assistant must build more of the scene and project
from the specification. Use a stronger model, expect iteration, and require the
same evidence before accepting completion.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| `octoscode` is not found after installation | Open a new terminal or load `$HOME/.cargo/env` |
| The TUI has flat colors or fails remotely | Set `TERM=xterm-256color` before launch |
| Provider test returns `401` | Recreate the DeepSeek key and confirm no whitespace was copied |
| Provider test returns `402` or a quota error | Check balance and account limits on the DeepSeek platform |
| The wrong model appears in `/status` | Select `deepseek-v4-pro` with `/model`, save, and restart the local server |
| The assistant asks for broad access | Start read-only, then grant workspace-write only when edits are required |

## Sources

- OctosCode repository and installation guide: <https://github.com/octos-org/octoscode>
- Octos runtime repository: <https://github.com/octos-org/octos>
- DeepSeek API quick start: <https://api-docs.deepseek.com/>
- DeepSeek model and pricing page: <https://api-docs.deepseek.com/quick_start/pricing/>
- DeepSeek API change log: <https://api-docs.deepseek.com/updates/>
- NIST CAISI DeepSeek V4 Pro evaluation: <https://www.nist.gov/news-events/news/2026/05/caisi-evaluation-deepseek-v4-pro>
- Artificial Analysis DeepSeek V4 Pro page: <https://artificialanalysis.ai/models/deepseek-v4-pro>

## Next Step

The next chapter adds Rerun and builds a static 3D scene on top of the Dora
environment created in the Hello World chapter.
