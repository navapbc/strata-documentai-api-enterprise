"""Submit traced work to a ThreadPoolExecutor without losing the parent trace.

OTel's Python SDK stores the active span in a contextvars.ContextVar. Worker
threads spawned by ThreadPoolExecutor don't inherit the submitting thread's
contextvars, so a span started inside a plain executor.submit(fn, ...) call
detaches from the caller's trace and is exported as an orphaned root span in
an unrelated trace, instead of nesting under the span that was active at
submission time.

submit_with_otel_context is a drop-in replacement for executor.submit that
captures the current context at the call site (the only place it's valid to
read from) and attaches it inside the worker before running fn. Use it
instead of executor.submit whenever fn may start an OTel span; there's no
separate context-capture step to forget or misplace.
"""

from collections.abc import Callable
from concurrent.futures import Executor, Future
from typing import Any, TypeVar

from opentelemetry import context as otel_context

_T = TypeVar("_T")


def submit_with_otel_context(executor: Executor, fn: Callable[..., _T], *args: Any) -> Future[_T]:
    """Submit fn(*args) to executor with the calling thread's OTel context attached."""
    ctx = otel_context.get_current()

    def _run() -> _T:
        token = otel_context.attach(ctx)
        try:
            return fn(*args)
        finally:
            otel_context.detach(token)

    return executor.submit(_run)
