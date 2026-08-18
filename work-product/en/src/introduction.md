# Introduction

This book is a practical guide to building Dora robotics applications and
systems with AI. It starts with the smallest useful dataflow, then gradually
adds visualization, reusable simulation scenes, sensor feedback, multimodal
perception, task planning, Agents, and multi-Agent coordination.

The goal is not to list every API. It is to help you understand how Dora
programs are organized, use AI to build and inspect runnable examples, and
connect those examples into increasingly capable robotics workflows.

By the end of the tutorial, you will also understand how to work effectively
with a coding assistant: describe goals, constraints, and acceptance criteria
clearly; use AI to help with environment setup, implementation, debugging, and
repetitive engineering work; and retain responsibility for validating key
decisions and runtime results.

## Video Tutorials

- [English video series on YouTube](https://www.youtube.com/watch?v=vtcaegVVe0c&list=PLWAJx-bWTTEo)
- [Chinese video series on Bilibili](https://www.bilibili.com/video/BV1Ljb16cEty)

## Tutorial Approach

Each chapter is built around a runnable slice:

- A short concept section explains the tool or workflow being introduced.
- A small example shows the minimum code needed to make the idea concrete.
- A verification script records the exact commands, package versions, and
  expected success markers.
- Visual chapters include screenshots, recordings, or assets generated from the
  verified example.

The examples are written so they can be copied, inspected, and modified. Local
paths, usernames, tokens, private hostnames, and machine-specific IDs are kept
out of the tutorial text.

## Two Ways to Build Every Example

Each project can be approached through one of two prompt routes. They teach the
same architecture and finish at the same acceptance checks, but begin from a
different amount of supplied work.

<div class="route-overview">
  <section class="route-overview__item route-overview__item--create">
    <span class="route-overview__label">Create route</span>
    <strong>Build from scratch</strong>
    <p>Ask the assistant to create the scene, assets, dataflow, interfaces, tests, and run scripts from an explicit specification. This route is more exploratory and needs a stronger model, more time, and a willingness to debug.</p>
  </section>
  <section class="route-overview__item route-overview__item--reproduce">
    <span class="route-overview__label">Reproduce route</span>
    <strong>Start from verified assets</strong>
    <p>Give the assistant the downloadable project and ask it to follow the pinned version matrix, single entry command, and acceptance markers. This route is more reliable and is the best way to build a working mental model quickly.</p>
  </section>
</div>

The two routes are not competing tracks. A useful progression is to reproduce
the example first, inspect the working system, and then return to the create
route to rebuild or change one layer. Every chapter marks the two prompts
clearly so they cannot be confused.

## Who This Is For

This book is intended for:

- New Dora users who want to run a complete example before reading deep API
  references.
- Robotics and embodied-AI learners who want to connect dataflow, visualization,
  and AI-assisted development.
- Developers who are comfortable with Python basics and command-line tools, but
  may be new to Dora, Rerun, or robot-style data pipelines.

You do not need to be a Rust developer to start. Rust and lower-level details can
be explored later, after the dataflow model feels familiar.

## How to Read

Start with the first chapter if you are new to Dora. It establishes the basic
installation and Hello World dataflow. The next chapter introduces Rerun through
a static scene, and the chapter after that uses Dora to make the same scene
move. Later chapters continue from that foundation.

When using the create route, ask the assistant to consult official documentation
and verify every external dependency. When using the reproduce route, the
chapter's `VERSIONS.md` and lock files are authoritative: do not let the
assistant silently upgrade packages, replace assets, or invent a second launch
path.

In both routes, completion means observed evidence, not an assistant saying
"done." Check the generated files, runtime markers, and final state described by
the chapter. If an entry runs in the background, wait for that exact process to
exit before deciding whether it passed.

## Learning Roadmap

This roadmap presents the tutorial as a continuous learning path. Each topic
builds on the runnable code, verification method, and concepts introduced
before it.

<div class="roadmap-grid">
  <a class="roadmap-item" href="weeks/preparation-llms-agents-coding-assistants.html"><span>Preparation</span><strong>LLMs, Agents, and Coding Assistants</strong><em>Choose a model and assistant, configure permissions, and connect OctosCode to DeepSeek.</em></a>
  <a class="roadmap-item" href="weeks/week-01-dora-introduction-installation-hello-world.html"><span>Foundations</span><strong>Dora and Hello World</strong><em>Dora introduction, installation guide, and Hello World example.</em></a>
  <a class="roadmap-item" href="weeks/week-02-rerun-scene-with-dora.html"><span>Visualization</span><strong>Rerun Static Scene</strong><em>Rerun visualization introduction, installation, initialization, and first static 3D scene.</em></a>
  <a class="roadmap-item" href="weeks/week-03-ai-assistant-rerun-workflow.html"><span>Motion</span><strong>Dora-Controlled Motion</strong><em>Use Dora and an AI assistant workflow to make the Rerun scene move.</em></a>
  <a class="roadmap-item" href="weeks/week-04-camera-data-visual-feedback.html"><span>Simulation</span><strong>Camera Sensors</strong><em>Use Habitat-Sim to generate RGB and depth data from a simulated wrist camera.</em></a>
  <a class="roadmap-item" href="weeks/week-07-multimodal-scene-understanding.html"><span>Perception</span><strong>Visual Analysis with Multimodal Models</strong><em>Use a local multimodal model to convert wrist-camera frames into structured JSON.</em></a>
  <a class="roadmap-item" href="weeks/week-08-sensor-data-scene-interaction.html"><span>Navigation</span><strong>LiDAR, SLAM, and Dora Navigation</strong><em>Build a LiDAR occupancy map and let Dora coordinate a Nav2 navigation task.</em></a>
  <a class="roadmap-item" href="weeks/week-09-llm-action-path-planning.html"><span>Planning</span><strong>LLM Tool and Skill Planning</strong><em>Turn a natural-language task into a validated JSON skill sequence and execute it with Dora.</em></a>
  <a class="roadmap-item" href="weeks/week-10-agent-task-planning.html"><span>Agents</span><strong>Agent Task Planning</strong><em>Integrate agent tooling for automated task planning.</em></a>
  <a class="roadmap-item" href="weeks/week-11-adora-octos-integration.html"><span>Multi-Agent Systems</span><strong>Continuous Supervision with Octos</strong><em>Coordinate observation, operation, and supervision through Dora to regulate temperature and pressure over time.</em></a>
</div>

Use the references page when you want to compare the tutorial against upstream
Dora, Rerun, and assistant documentation.
