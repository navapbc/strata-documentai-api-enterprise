"""Cross-platform task runner. Works anywhere Python and uv are available.

Usage:
    uv run tasks.py <command> [args...]
    uv run tasks.py test
    uv run tasks.py lint
    uv run tasks.py format
    uv run tasks.py check
    uv run tasks.py dev
"""

import subprocess
import sys


def _run(*cmd: str) -> int:
    _echo(" ".join(cmd))
    return subprocess.call(cmd)


def _echo(msg: str) -> None:
    print(f"\033[36m> {msg}\033[0m", flush=True)


def _uv(*cmd: str) -> int:
    return _run("uv", "run", "--frozen", *cmd)


# =============================================================================
# Testing
# =============================================================================


def test() -> int:
    """Run test suite."""
    return _uv("pytest", *sys.argv[2:])


def test_coverage() -> int:
    """Run tests with coverage report."""
    return _uv(
        "pytest",
        "--cov=src/documentai_api",
        "--cov-branch",
        "--cov-report=html:.coverage_report",
        "--cov-report=term-missing",
        *sys.argv[2:],
    )


def test_parallel() -> int:
    """Run test suite in parallel."""
    return _uv("pytest", "-n", "auto", *sys.argv[2:])


def test_audit() -> int:
    """Run audit logging tests."""
    return _uv("pytest", "-m", "audit", *sys.argv[2:])


# =============================================================================
# Formatting
# =============================================================================


def format_() -> int:
    """Format code."""
    return _uv("ruff", "format", ".")


def format_check() -> int:
    """Check code formatting without modifying."""
    return _uv("ruff", "format", "--check", ".")


# =============================================================================
# Linting
# =============================================================================


def lint() -> int:
    """Run all linters (with auto-fix)."""
    ret = lint_ruff()
    if ret != 0:
        return ret
    ret = lint_uv()
    if ret != 0:
        return ret
    return lint_mypy()


def lint_check() -> int:
    """Run all linters (read-only, no fixes)."""
    ret = lint_ruff_check()
    if ret != 0:
        return ret
    ret = lint_uv()
    if ret != 0:
        return ret
    return lint_mypy()


def lint_ruff() -> int:
    """Lint Python code with ruff (auto-fix)."""
    return _uv("ruff", "check", "--fix", ".")


def lint_ruff_check() -> int:
    """Lint Python code with ruff (read-only)."""
    return _uv("ruff", "check", ".")


def lint_mypy() -> int:
    """Type check with mypy."""
    return _uv("mypy", "src")


def typecheck() -> int:
    """Type check with mypy (alias for lint-mypy)."""
    return lint_mypy()


def lint_uv() -> int:
    """Check uv lockfile is up-to-date."""
    # Uses 'uv lock' directly, not 'uv run', because we're checking the
    # lockfile itself rather than running a command inside the environment.
    return _run("uv", "lock", "--check")


# =============================================================================
# Composite tasks
# =============================================================================


def check() -> int:
    """Run all checks (read-only: format check, lint check, test)."""
    for task in (format_check, lint_check, test):
        ret = task()
        if ret != 0:
            return ret
    return 0


def precommit() -> int:
    """Pre-push workflow: format, lint (with fix), test."""
    for task in (format_, lint, test):
        ret = task()
        if ret != 0:
            return ret
    return 0


# =============================================================================
# Run
# =============================================================================


def start() -> int:
    """Run the application server (production mode)."""
    return _uv("documentai_api")


def dev() -> int:
    """Run the application server with reload."""
    return _uv("uvicorn", "documentai_api.app:app", "--reload", *sys.argv[2:])


# =============================================================================
# Utilities
# =============================================================================


def openapi_spec() -> int:
    """Export OpenAPI spec to docs directory."""
    from pathlib import Path

    output = Path(__file__).parent.parent / "docs" / "documentai-api" / "openapi.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    _echo(f"export-openapi > {output}")
    result = subprocess.run(
        ["uv", "run", "--frozen", "export-openapi"], capture_output=True, text=True
    )
    if result.returncode != 0:
        print(result.stderr)
        return result.returncode
    output.write_text(result.stdout)
    return 0


def clean() -> int:
    """Clean build artifacts."""
    import shutil
    from pathlib import Path

    _echo("removing __pycache__, .pytest_cache, .coverage_report")
    for d in Path(".").rglob("__pycache__"):
        shutil.rmtree(d, ignore_errors=True)
    for d in (".pytest_cache", ".coverage_report", ".coverage"):
        shutil.rmtree(d, ignore_errors=True)
    return 0


def help_() -> int:
    """Show available tasks."""
    print("\nAvailable tasks:\n")
    for name, func in sorted(_TASKS.items()):
        print(f"  {name:<20} {func.__doc__ or ''}")
    print("\nUsage: uv run tasks.py <task> [args...]\n")
    return 0


# =============================================================================
# Dispatcher
# =============================================================================

_TASKS = {
    name.rstrip("_"): func
    for name, func in globals().items()
    if callable(func)
    and not name.startswith("_")
    and getattr(func, "__module__", None) == "__main__"
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        raise SystemExit(help_())

    task_name = sys.argv[1].replace("-", "_")
    task_fn = _TASKS.get(task_name)

    if task_fn is None:
        print(f"Unknown task: {sys.argv[1]}")
        help_()
        raise SystemExit(1)

    try:
        raise SystemExit(task_fn())
    except KeyboardInterrupt:
        raise SystemExit(130) from None
