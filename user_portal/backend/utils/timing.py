"""
Timing utilities — lightweight per-node elapsed-time instrumentation.

Used to pinpoint slow stages in the LangGraph pipeline (e.g., schema_linker,
logic_check) without pulling in a full tracing/metrics dependency.

Emits logs in a grep-friendly format:
    [timing] node=<name> elapsed=<ms>ms [extra=kv ...]
"""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from functools import wraps
from typing import Any, Awaitable, Callable

logger = logging.getLogger("pipeline.timing")


def timed_node(label: str | None = None) -> Callable:
    """Decorator for async pipeline nodes that logs elapsed wall-clock time.

    Usage:
        @timed_node("schema_linker")
        async def schema_linker_node(state):
            ...
    """

    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        name = label or func.__name__

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            try:
                return await func(*args, **kwargs)
            finally:
                elapsed_ms = (time.perf_counter() - start) * 1000
                logger.info("[timing] node=%s elapsed=%.0fms", name, elapsed_ms)

        return wrapper

    return decorator


@contextmanager
def timed_span(name: str, **extra: Any):
    """Sync context manager for timing sub-steps inside a node.

    Usage:
        with timed_span("schema_linker.pull_value_samples", tables=len(tables)):
            ...
    """
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000
        if extra:
            kv = " ".join(f"{k}={v}" for k, v in extra.items())
            logger.info("[timing] span=%s elapsed=%.0fms %s", name, elapsed_ms, kv)
        else:
            logger.info("[timing] span=%s elapsed=%.0fms", name, elapsed_ms)


class AsyncTimedSpan:
    """Async context manager variant of `timed_span` (for `async with`)."""

    def __init__(self, name: str, **extra: Any) -> None:
        self.name = name
        self.extra = extra
        self._start: float = 0.0

    async def __aenter__(self) -> "AsyncTimedSpan":
        self._start = time.perf_counter()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        elapsed_ms = (time.perf_counter() - self._start) * 1000
        if self.extra:
            kv = " ".join(f"{k}={v}" for k, v in self.extra.items())
            logger.info("[timing] span=%s elapsed=%.0fms %s", self.name, elapsed_ms, kv)
        else:
            logger.info("[timing] span=%s elapsed=%.0fms", self.name, elapsed_ms)
