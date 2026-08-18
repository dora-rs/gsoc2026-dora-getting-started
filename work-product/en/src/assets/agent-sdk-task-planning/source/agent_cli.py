#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os

from agents import (
    Agent,
    ModelSettings,
    OpenAIChatCompletionsModel,
    Runner,
    set_tracing_disabled,
)
from openai import AsyncOpenAI

from agent_tools import (
    AGENT_INSTRUCTIONS,
    EventPrinter,
    RobotApiClient,
    build_tools,
)


DEFAULT_TASK = "查看指示灯；如果亮着就关闭开关，确认灯灭后回到起点。"


def build_agent(
    client: RobotApiClient,
    events: EventPrinter,
    *,
    model_name: str | None = None,
    ollama_url: str | None = None,
):
    set_tracing_disabled(True)
    ollama = AsyncOpenAI(
        base_url=ollama_url
        or os.getenv(
            "OLLAMA_OPENAI_BASE_URL", "http://127.0.0.1:11434/v1"
        ),
        api_key="ollama",
    )
    model = OpenAIChatCompletionsModel(
        model=model_name
        or os.getenv("OLLAMA_MODEL", "qwen3-vl:8b-instruct"),
        openai_client=ollama,
    )
    return Agent(
        name="Dora robot operator",
        instructions=AGENT_INSTRUCTIONS,
        model=model,
        model_settings=ModelSettings(
            temperature=0.0,
            parallel_tool_calls=False,
        ),
        tools=build_tools(client, events),
    )


def run_task(task: str) -> str:
    events = EventPrinter()
    events.emit("INPUT", task)
    client = RobotApiClient(
        os.getenv("AGENT_TASK_API_URL", "http://127.0.0.1:8000")
    )
    result = Runner.run_sync(
        build_agent(client, events),
        task,
        max_turns=30,
    )
    final = str(result.final_output)
    events.emit("DONE", final)
    return final


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", help="Run one instruction and exit.")
    args = parser.parse_args()
    if args.task:
        run_task(args.task)
        return
    print("Dora robot agent. Type 'exit' to quit.", flush=True)
    while True:
        try:
            task = input("task> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if task.lower() in {"exit", "quit"}:
            break
        if task:
            run_task(task)


if __name__ == "__main__":
    main()
