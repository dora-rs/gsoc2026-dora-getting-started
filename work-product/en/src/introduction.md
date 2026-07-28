# Introduction

This book is a practical getting-started guide for Dora. It starts with the
smallest useful dataflow, then gradually adds visualization, reusable scene
assets, sensor feedback, multimodal perception, and task planning.

The goal is not to list every API. The goal is to help a new user build a mental
model of how Dora programs are organized, run a verified example, and then keep
expanding that example into a more capable embodied-AI workflow.

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

When a chapter includes commands, run them in the verification directory named at
the top of that chapter. When the tutorial mentions an AI coding assistant, ask
it to check the latest official documentation before it chooses package names,
commands, or APIs.

## Learning Roadmap

This roadmap presents the tutorial as a continuous learning path. Each topic
builds on the runnable code, verification method, and concepts introduced
before it.

<div class="roadmap-grid">
  <a class="roadmap-item" href="weeks/week-01-dora-introduction-installation-hello-world.html"><span>Foundations</span><strong>Dora and Hello World</strong><em>Dora and adora introduction, installation guide, and Hello World example.</em></a>
  <a class="roadmap-item" href="weeks/week-02-rerun-scene-with-dora.html"><span>Visualization</span><strong>Rerun Static Scene</strong><em>Rerun visualization introduction, installation, initialization, and first static 3D scene.</em></a>
  <a class="roadmap-item" href="weeks/week-03-ai-assistant-rerun-workflow.html"><span>Motion</span><strong>Dora-Controlled Motion</strong><em>Use Dora and an AI assistant workflow to make the Rerun scene move.</em></a>
  <a class="roadmap-item" href="weeks/week-04-camera-data-visual-feedback.html"><span>Simulation</span><strong>Camera Sensors</strong><em>Use Habitat-Sim to generate RGB and depth data from a simulated wrist camera.</em></a>
  <a class="roadmap-item" href="weeks/week-07-multimodal-scene-understanding.html"><span>Perception</span><strong>Visual Analysis with Multimodal Models</strong><em>Use a local multimodal model to convert wrist-camera frames into structured JSON.</em></a>
  <a class="roadmap-item" href="weeks/week-08-sensor-data-scene-interaction.html"><span>Navigation</span><strong>LiDAR, SLAM, and Dora Navigation</strong><em>Build a LiDAR occupancy map and let Dora coordinate a Nav2 navigation task.</em></a>
  <a class="roadmap-item" href="weeks/week-09-llm-action-path-planning.html"><span>Planning</span><strong>LLM Action Planning</strong><em>Plan action paths using large language models.</em></a>
  <a class="roadmap-item" href="weeks/week-10-agent-task-planning.html"><span>Agents</span><strong>Agent Task Planning</strong><em>Integrate agent tooling for automated task planning.</em></a>
  <a class="roadmap-item" href="weeks/week-11-adora-octos-integration.html"><span>Integration</span><strong>adora and Octos</strong><em>Explore advanced adora and Octos integration for intelligent robot control.</em></a>
  <a class="roadmap-item" href="weeks/week-12-final-consolidation.html"><span>Complete System</span><strong>End-to-End Robotics Workflow</strong><em>Connect perception, planning, actions, visualization, and runtime checks.</em></a>
  <a class="roadmap-item" href="weeks/final-week-work-product-submission.html"><span>Next Steps</span><strong>Verification and Extension</strong><em>Verify the complete example and identify practical ways to extend it.</em></a>
</div>

Use the references page when you want to compare the tutorial against upstream
Dora, Rerun, and assistant documentation.
