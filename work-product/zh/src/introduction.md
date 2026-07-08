# 导言

这本书是一份面向 Dora 的实践型入门教程。它从最小可用的 dataflow 开始，然后逐步加入可视化、可复用场景资产、传感器反馈、多模态感知和任务规划。

它的目标不是罗列所有 API，而是帮助新用户建立 Dora 程序如何组织的直觉：先跑通一个经过验证的例子，再把这个例子逐步扩展成更完整的 embodied-AI 工作流。

## 教程思路

每一章都围绕一个可运行的小切片展开：

- 先用简短章节解释本章引入的工具或工作流。
- 再用一个小示例把概念落到具体代码上。
- 通过验证脚本记录实际命令、软件版本和成功标记。
- 涉及可视化的章节会包含由验证示例生成的截图、录屏或资产。

示例代码应该能被复制、检查和修改。教程正文中不会保留本地绝对路径、用户名、token、私有主机名或机器相关 ID。

## 适合人群

这本书适合：

- 想先跑通完整示例，再深入阅读 API 文档的新 Dora 用户。
- 希望把 dataflow、可视化和 AI 辅助开发串起来理解的 robotics 与 embodied-AI 学习者。
- 熟悉 Python 基础和命令行工具，但还不熟悉 Dora、Rerun 或机器人数据流水线的开发者。

开始阅读不需要你已经是 Rust 开发者。Rust 和更底层的实现细节可以在理解 dataflow 模型之后再继续探索。

## 阅读方式

如果你刚接触 Dora，请从第一章开始。第一章建立安装和 Hello World dataflow 的基础；下一章通过静态场景引入 Rerun；再下一章使用 Dora 让同一个场景动起来。后续章节会继续沿着这个基础扩展。

当章节中包含命令时，请在该章节开头标注的 verification 目录中运行。遇到 AI 编程助手相关内容时，最好明确要求它先检查最新官方文档，再决定包名、命令和 API。

## 学习路线

这份路线图用于保持整本书的结构清晰。随着内容推进，每个 week 都应该变成可阅读的章节，并配套可运行代码、验证记录和视频素材。

<div class="roadmap-grid">
  <a class="roadmap-item" href="weeks/week-01-dora-introduction-installation-hello-world.html"><span>Week 1</span><strong>Dora 与 Hello World</strong><em>Dora 与 adora 介绍、安装指南和 Hello World 示例。</em></a>
  <a class="roadmap-item" href="weeks/week-02-rerun-scene-with-dora.html"><span>Week 2</span><strong>Rerun 静态场景</strong><em>Rerun 可视化介绍、安装、初始化，以及第一个静态 3D 场景。</em></a>
  <a class="roadmap-item" href="weeks/week-03-ai-assistant-rerun-workflow.html"><span>Week 3</span><strong>Dora 控制运动</strong><em>使用 Dora 和 AI 助手工作流，让 Rerun 场景动起来。</em></a>
  <a class="roadmap-item" href="weeks/week-04-camera-data-visual-feedback.html"><span>Week 4</span><strong>相机传感器</strong><em>使用 Habitat-Sim 从仿真 wrist camera 生成 RGB 和 depth data。</em></a>
  <a class="roadmap-item" href="weeks/week-05-consolidation-refinement.html"><span>Week 5</span><strong>内容整合</strong><em>整合前几章内容，完善文档、示例和视频。</em></a>
  <a class="roadmap-item" href="weeks/week-06-midterm-work-product.html"><span>Week 6</span><strong>Midterm 准备</strong><em>准备 midterm work products，并验证目前的学习路径。</em></a>
  <a class="roadmap-item" href="weeks/week-07-multimodal-scene-understanding.html"><span>Week 7</span><strong>多模态理解</strong><em>集成开源多模态模型，分析场景视觉信息。</em></a>
  <a class="roadmap-item" href="weeks/week-08-sensor-data-scene-interaction.html"><span>Week 8</span><strong>Sensor Interaction</strong><em>获取更多 sensor data，并扩展场景交互能力。</em></a>
  <a class="roadmap-item" href="weeks/week-09-llm-action-path-planning.html"><span>Week 9</span><strong>LLM 动作规划</strong><em>使用大语言模型规划动作路径。</em></a>
  <a class="roadmap-item" href="weeks/week-10-agent-task-planning.html"><span>Week 10</span><strong>Agent 任务规划</strong><em>集成 agent 工具，实现自动化任务规划。</em></a>
  <a class="roadmap-item" href="weeks/week-11-adora-octos-integration.html"><span>Week 11</span><strong>adora 与 Octos</strong><em>探索 adora 与 Octos 的高级集成，构建更智能的机器人控制体验。</em></a>
  <a class="roadmap-item" href="weeks/week-12-final-consolidation.html"><span>Week 12</span><strong>最终整合</strong><em>最终整合文档、可运行示例和视频。</em></a>
  <a class="roadmap-item" href="weeks/final-week-work-product-submission.html"><span>Final Week</span><strong>最终提交</strong><em>打包最终工作产出，完成最终 review materials。</em></a>
</div>

需要和 Dora、Rerun 或 AI 助手的上游资料对照时，可以查看参考资料页。
