from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import TypeVar


T = TypeVar("T")


def run_parallel(tasks: dict[str, Callable[[], T]]) -> dict[str, T]:
    with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
        futures = {
            name: executor.submit(task) for name, task in tasks.items()
        }
        return {name: future.result() for name, future in futures.items()}
