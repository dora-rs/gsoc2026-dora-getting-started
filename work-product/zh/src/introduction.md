# 导言

这份教程通过一个经过本地验证的 Hello World dataflow 介绍 Dora。它优先覆盖新用户最先需要的内容：Dora 是什么，如何安装当前 CLI 和 Python 包，dataflow 如何连接，以及如何确认示例真的运行成功。

示例命令默认面向 Windows PowerShell 编写。每个可运行教程会在开头列出相关操作系统、软件、程序和库版本；正文中不保留本地绝对路径、用户名、token 或机器相关 ID。

## 你会构建什么

第一个 dataflow 包含两个 Python 节点：

- `talker.py` 接收定时器 tick，并发布一个 Apache Arrow 字符串。
- `listener.py` 订阅这条消息并打印。
- `dataflow.yml` 声明两个节点如何连接。

从下一章开始即可。需要和 Dora 上游资料对照时，可以查看参考资料页。
