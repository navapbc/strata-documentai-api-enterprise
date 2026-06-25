"""Base infrastructure validator with shared helpers and result types."""

import json
import sys
from dataclasses import dataclass, field

from validators.constants import DriftStatus

_TTY = sys.stdout.isatty()


class Color:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def style(text: str, *codes: str) -> str:
    if not _TTY:
        return text
    return "".join(codes) + text + Color.RESET


@dataclass
class Result:
    category: str
    rtype: str
    name: str
    status: str
    drift: list[str] = field(default_factory=list)
    error: str | None = None


class BaseValidator:
    """Mixin providing result recording helpers.

    Attributes are populated by InfraValidator.__init__ at composition time.
    Validator mixins reference these via self.
    """

    results: list[Result]
    component_resources: dict[str, list[str]]
    planned_tf_resources: dict
    service_name: str
    project: str
    env: str
    ssm_prefix: str
    account_id: str

    def record(
        self,
        category: str,
        rtype: str,
        name: str,
        status: str,
        drift: list[str] | None = None,
        error: str | None = None,
    ):
        self.results.append(Result(category, rtype, name, status, drift or [], error))

    def ok(self, cat: str, rtype: str, name: str):
        self.record(cat, rtype, name, DriftStatus.PRESENT)

    def missing(self, cat: str, rtype: str, name: str, error: str | None = None):
        self.record(cat, rtype, name, DriftStatus.MISSING, error=error)

    def drifted(self, cat: str, rtype: str, name: str, drift: list[str]):
        self.record(cat, rtype, name, DriftStatus.DRIFTED, drift=drift)

    def check_or_drift(self, cat: str, rtype: str, name: str, drift: list[str]):
        if drift:
            self.drifted(cat, rtype, name, drift)
        else:
            self.ok(cat, rtype, name)


def print_report(results: list[Result], as_json: bool) -> int:
    """Print results and return exit code (0=clean, 1=issues found)."""
    if as_json:
        print(
            json.dumps(
                [
                    {
                        "category": r.category,
                        "type": r.rtype,
                        "name": r.name,
                        "status": r.status,
                        "drift": r.drift,
                        "error": r.error,
                    }
                    for r in results
                ],
                indent=2,
            )
        )
        missing = sum(1 for r in results if r.status == DriftStatus.MISSING)
        drifted = sum(1 for r in results if r.status == DriftStatus.DRIFTED)
        return 0 if (missing + drifted) == 0 else 1

    counts = {DriftStatus.PRESENT: 0, DriftStatus.MISSING: 0, DriftStatus.DRIFTED: 0}
    for r in results:
        counts[r.status] += 1
        if r.status == DriftStatus.PRESENT:
            icon = style("✓", Color.GREEN)
        elif r.status == DriftStatus.MISSING:
            icon = style("✗", Color.RED)
        else:
            icon = style("~", Color.YELLOW)
        print(f"  {icon}  {style(r.rtype, Color.BOLD):40s}  {r.name}")
        for d in r.drift:
            print(f"       {style('DRIFT', Color.YELLOW)}  {d}")
        if r.error:
            print(f"       {style('ERROR', Color.RED)}  {r.error}")

    total = sum(counts.values())
    present = f"{counts[DriftStatus.PRESENT]} present"
    missing_str = f"{counts[DriftStatus.MISSING]} missing"
    drifted_str = f"{counts[DriftStatus.DRIFTED]} drifted"
    print(f"\n{'─' * 70}")
    print(
        f"  {total} checks:  "
        f"{style(present, Color.GREEN)}  ·  "
        f"{style(missing_str, Color.RED)}  ·  "
        f"{style(drifted_str, Color.YELLOW)}"
    )
    print(f"{'─' * 70}\n")

    return 0 if (counts[DriftStatus.MISSING] + counts[DriftStatus.DRIFTED]) == 0 else 1
