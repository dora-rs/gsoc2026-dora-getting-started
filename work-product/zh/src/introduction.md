# 导言

这本书是一份使用 AI 开发 Dora 机器人应用与系统的实践教程。它从最小可用的
dataflow 开始，然后逐步加入可视化、可复用仿真场景、传感器反馈、多模态感知、
任务规划、Agent 和多 Agent 协作。

它的目标不是罗列所有 API，而是帮助你理解 Dora 程序如何组织，使用 AI 构建并
检查可运行的示例，再把这些示例连接成能力逐步增强的机器人工作流。

## 教程思路

每一章都围绕一个可运行的小切片展开：

- 先用简短章节解释本章引入的工具或工作流。
- 再用一个小示例把概念落到具体代码上。
- 通过验证脚本记录实际命令、软件版本和成功标记。
- 涉及可视化的章节会包含由验证示例生成的截图、录屏或资产。

示例代码应该能被复制、检查和修改。教程正文中不会保留本地绝对路径、用户名、token、私有主机名或机器相关 ID。

## 每个示例的两种完成方式

每个工程都可以选择两种提示词路线。它们讲解相同的架构，也使用相同的验收条件，
区别在于开始时已经提供了多少内容。

<div class="route-overview">
  <section class="route-overview__item route-overview__item--create">
    <span class="route-overview__label">创造路线</span>
    <strong>从零开始搭建</strong>
    <p>根据明确的需求，让助手创建场景、资产、dataflow、接口、测试和运行脚本。这条路线探索性更强，需要能力较强的模型、更多时间，也更适合喜欢调试和深入理解实现的开发者。</p>
  </section>
  <section class="route-overview__item route-overview__item--reproduce">
    <span class="route-overview__label">复现路线</span>
    <strong>使用已验证资产</strong>
    <p>把可下载工程交给助手，让它严格使用固定版本、唯一入口和验收标记。这条路线成功率更高，适合能力较弱的助手，也适合希望快速跑通示例并建立整体思维模型的读者。</p>
  </section>
</div>

两条路线并不冲突。一个实用的顺序是先复现可运行工程，理解系统如何连接，再回到
创造路线，重新搭建或替换其中一层。每章都会明显标出两类提示词，避免混用。

## 适合人群

这本书适合：

- 想先跑通完整示例，再深入阅读 API 文档的新 Dora 用户。
- 希望把 dataflow、可视化和 AI 辅助开发串起来理解的 robotics 与 embodied-AI 学习者。
- 熟悉 Python 基础和命令行工具，但还不熟悉 Dora、Rerun 或机器人数据流水线的开发者。

开始阅读不需要你已经是 Rust 开发者。Rust 和更底层的实现细节可以在理解 dataflow 模型之后再继续探索。

## 阅读方式

如果你刚接触 Dora，请从第一章开始。第一章建立安装和 Hello World dataflow 的基础；下一章通过静态场景引入 Rerun；再下一章使用 Dora 让同一个场景动起来。后续章节会继续沿着这个基础扩展。

使用创造路线时，应要求助手查阅官方文档，并验证每个外部依赖。使用复现路线时，
章节工程中的 `VERSIONS.md` 和 lock 文件是唯一版本依据，不要让助手自行升级依赖、
替换资产或创造第二套启动方式。

两条路线都不能把助手声称“完成”当作成功。应检查章节列出的生成文件、运行时标记
和最终状态。如果入口在后台运行，必须等待该进程真正结束后再判断结果。

## 学习路线

这份路线图把教程组织成一条连续的学习路径。每个主题都会建立在前面已经完成的可运行代码、验证方法和概念之上。

<div class="roadmap-grid">
  <a class="roadmap-item" href="weeks/week-01-dora-introduction-installation-hello-world.html"><span>基础</span><strong>Dora 与 Hello World</strong><em>Dora 介绍、安装指南和 Hello World 示例。</em></a>
  <a class="roadmap-item" href="weeks/week-02-rerun-scene-with-dora.html"><span>可视化</span><strong>Rerun 静态场景</strong><em>Rerun 可视化介绍、安装、初始化，以及第一个静态 3D 场景。</em></a>
  <a class="roadmap-item" href="weeks/week-03-ai-assistant-rerun-workflow.html"><span>运动控制</span><strong>Dora 控制运动</strong><em>使用 Dora 和 AI 助手工作流，让 Rerun 场景动起来。</em></a>
  <a class="roadmap-item" href="weeks/week-04-camera-data-visual-feedback.html"><span>仿真</span><strong>相机传感器</strong><em>使用 Habitat-Sim 从仿真 wrist camera 生成 RGB 和 depth data。</em></a>
  <a class="roadmap-item" href="weeks/week-07-multimodal-scene-understanding.html"><span>场景感知</span><strong>用多模态模型分析视觉信息</strong><em>使用本地多模态模型把腕部摄像机图像转换成结构化 JSON。</em></a>
  <a class="roadmap-item" href="weeks/week-08-sensor-data-scene-interaction.html"><span>导航</span><strong>激光雷达、SLAM 与 Dora 导航</strong><em>构建激光占据地图，并让 Dora 协调 Nav2 完成导航任务。</em></a>
  <a class="roadmap-item" href="weeks/week-09-llm-action-path-planning.html"><span>动作规划</span><strong>LLM 工具与 Skill 规划</strong><em>把自然语言任务转换成经过校验的 JSON skill 序列，并由 Dora 执行。</em></a>
  <a class="roadmap-item" href="weeks/week-10-agent-task-planning.html"><span>Agent</span><strong>Agent 任务规划</strong><em>集成 agent 工具，实现自动化任务规划。</em></a>
  <a class="roadmap-item" href="weeks/week-11-adora-octos-integration.html"><span>多 Agent 系统</span><strong>Octos 持续过程监督</strong><em>让观察、操作和监督角色通过 Dora 协作，持续控制温度与压力。</em></a>
</div>

需要和 Dora、Rerun 或 AI 助手的上游资料对照时，可以查看参考资料页。
