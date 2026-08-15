# Dora Hello World 验证工程

这个工程使用固定版本验证 Dora 安装和最小 talker/listener dataflow。

在 Windows PowerShell 中运行：

```powershell
./run.ps1 -Seconds 4
```

脚本会创建工程内 `.venv`，安装 `requirements.txt`，下载并校验固定的 Dora CLI，
运行四秒 dataflow，并检查 `listener received: Hello from dora-rs`。

使用 AI 编程助手复现时，先读取 `VERSIONS.md`、`TUTORIAL_CONTRACT.md`、
`ASSET_GUIDE.md` 和 `READER_PROMPT.md`。唯一 Windows 入口是
`./run.ps1 -Seconds 4`。
