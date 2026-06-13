# Introduction

This tutorial introduces Dora through a small, verified Hello World dataflow. It
focuses on the parts a new user needs first: what Dora is, how to install the
current CLI and Python package, how a dataflow is wired, and how to confirm the
example really ran.

The examples are designed for copyable PowerShell commands on Windows, with
version information called out near the top of each runnable tutorial. Local
paths, usernames, tokens, and machine-specific IDs are omitted from the text.

## What You Will Build

The first dataflow has two Python nodes:

- `talker.py` receives timer ticks and publishes an Apache Arrow string.
- `listener.py` subscribes to that message and prints it.
- `dataflow.yml` declares how the nodes connect.

Start with the next chapter, then use the references page when you want to
compare the tutorial against upstream Dora documentation.
