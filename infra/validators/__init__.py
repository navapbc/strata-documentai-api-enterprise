"""Base infrastructure validator with shared helpers and result types."""

import json
import sys
from dataclasses import dataclass, field

_TTY = sys.stdout.isatty()


def _c(text: str, code: str) -> str:
    return f"{code}{text}\033[0m" if _TTY else text


def green(t: str) -> str:
    return _c(t, "\033[92m")


def red(t: str) -> str:
    return _c(t, "\033[91m")


def yellow(t: str) -> str:
    return _c(t, "\033[93m")


def bold(t: str) -> str:
    return _c(t, "\033[1m")


@dataclass
class Result:
    category: str
    rtype: str
    name: str
    status: str  # PRESENT | MISSING | DRIFTED
    drift: list[str] = field(default_factory=list)
    error: str | None = None


class BaseValidator:
    """Mixin providing result recording helpers.

    Attributes are populated by InfraValidator.__init__ at composition time.
    Validator mixins reference these via self.
    """

    results: list[Result]
    component_resources: dict[str, list[str]]
    sn: str
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
        self.record(cat, rtype, name, "PRESENT")

    def missing(self, cat: str, rtype: str, name: str, error: str | None = None):
        self.record(cat, rtype, name, "MISSING", error=error)

    def drifted(self, cat: str, rtype: str, name: str, drift: list[str]):
        self.record(cat, rtype, name, "DRIFTED", drift=drift)

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
        missing = sum(1 for r in results if r.status == "MISSING")
        drifted = sum(1 for r in results if r.status == "DRIFTED")
        return 0 if (missing + drifted) == 0 else 1

    counts = {"PRESENT": 0, "MISSING": 0, "DRIFTED": 0}
    for r in results:
        counts[r.status] += 1
        if r.status == "PRESENT":
            icon = green("✓")
        elif r.status == "MISSING":
            icon = red("✗")
        else:
            icon = yellow("~")
        print(f"  {icon}  {bold(r.rtype):40s}  {r.name}")
        for d in r.drift:
            print(f"       {yellow('DRIFT')}  {d}")
        if r.error:
            print(f"       {red('ERROR')}  {r.error}")

    total = sum(counts.values())
    present = f"{counts['PRESENT']} present"
    missing_str = f"{counts['MISSING']} missing"
    drifted_str = f"{counts['DRIFTED']} drifted"
    print(f"\n{'─' * 70}")
    print(
        f"  {total} checks:  "
        f"{green(present)}  ·  "
        f"{red(missing_str)}  ·  "
        f"{yellow(drifted_str)}"
    )
    print(f"{'─' * 70}\n")

    return 0 if (counts["MISSING"] + counts["DRIFTED"]) == 0 else 1
