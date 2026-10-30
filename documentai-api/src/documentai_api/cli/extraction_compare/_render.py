import dataclasses
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from documentai_api.utils.md import to_table

_TEMPLATES_DIR = Path(__file__).parent / "templates"


def _make_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(_TEMPLATES_DIR),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["to_table"] = to_table
    return env


_ENV = _make_env()


def render_template(name: str, ctx: object) -> str:
    """Render a Jinja2 template by filename with the given context."""
    d = (
        dataclasses.asdict(ctx)
        if dataclasses.is_dataclass(ctx) and not isinstance(ctx, type)
        else ctx
    )
    return _ENV.get_template(name).render(d)
