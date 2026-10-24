#!/usr/bin/env python3
"""Guard checks for locked rulings that a stale doc could walk an agent back into.

Each check cites the ruling it enforces. Checks are deterministic (paths and
grep). They report by default. Pass --strict to exit nonzero on any failure,
which is how they would be wired into the verification gates once the open
items they flag are closed.

Usage:
  python3 scripts/docs-guard.py            # report
  python3 scripts/docs-guard.py --strict   # exit 1 on any failure
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
# The scope the checks run over. A consumer swaps these for its own
# paths; they are set to the layout of the repo this reference was
# written against, so adapt them before use.
RUNTIME_SCOPE = ["src/runtime", "src/api"]
COPY_SCOPE = ["src/copy", "src/components"]
SKIP = re.compile(r"\.(test|stories)\.[jt]sx?$|/node_modules/|\.stories\.")


@dataclass
class Check:
    name: str
    ruling: str
    why: str
    kind: str  # "absent" = these paths must not exist; "forbid" = this regex must not appear
    targets: list[str]
    pattern: str | None = None


# The EXAMPLE checks. They are here to show the SHAPE of a ruling
# ledger: one row per ruling, each row naming where the ruling came
# from and why it is a rule. The rulings themselves are this repo's
# own; a consumer replaces them with its own.
CHECKS = [
    Check(
        "no retired route files",
        "the routing decision",
        "A retired route stays deleted. A file left behind is a route "
        "somebody can still reach.",
        "absent",
        ["src/routes/retired*", "src/routes/**/legacy-*"],
    ),
    Check(
        "the live route is the only one",
        "the routing decision",
        "There is one entry point. The old names are gone, and the live "
        "gateway is NOT on this list, because it is supposed to be there.",
        "absent",
        ["src/routes/api/retired.ts", "src/routes/api/legacy.ts"],
    ),
    Check(
        "the sanctioned deploy workflow exists",
        "the deploy law",
        "No ad-hoc workflows. The one sanctioned deploy workflow MUST "
        "exist, so a deploy cannot quietly stop having a home.",
        "require",
        [".github/workflows/deploy.yml"],
    ),
    Check(
        "no inert module imports in runtime code",
        "the dead-code decision",
        "The module is inert; any runtime import of it is a defect.",
        "forbid",
        RUNTIME_SCOPE,
        r"from\s+['\"]@/lib/inert['\"]",
    ),
    Check(
        "no retired vendor references in runtime code",
        "the vendor decision",
        "The retired vendor is not in the product. Word boundaries keep "
        "a similarly named vendor from matching.",
        "forbid",
        RUNTIME_SCOPE,
        r"(?i)\b(retiredvendor|othervendor)\b",
    ),
    Check(
        "no retired wording in user copy",
        "the copy decision",
        "Say the current name. The old one is retired.",
        "forbid",
        COPY_SCOPE,
        r"(?i)hosted[ -]credits?",
    ),
    Check(
        "no cut plan names in user copy",
        "the pricing decision",
        "One plan plus credit packs. The cut names are cut.",
        "forbid",
        ["src/copy"],
        r"(?i)legacy plan|expired plan|\bold plan\b",
    ),
]


def iter_files(scope: list[str]):
    for root in scope:
        base = REPO / root
        if base.is_file():
            yield base
        elif base.exists():
            for p in base.rglob("*"):
                if p.is_file() and p.suffix in {".ts", ".tsx", ".js", ".jsx", ".py", ".json", ".md"} and not SKIP.search(p.as_posix()):
                    yield p


def run(check: Check) -> list[str]:
    """Evaluate one check.

    Kinds: ``absent`` (targets must not exist), ``require`` (targets must
    exist, by the deploy law), ``forbid`` (regex must not appear inside
    the target scope).
    """
    hits: list[str] = []
    if check.kind == "absent":
        for target in check.targets:
            for match in REPO.glob(target):
                hits.append(match.relative_to(REPO).as_posix())
    elif check.kind == "require":
        for target in check.targets:
            if not (REPO / target).exists():
                hits.append(f"missing: {target}")
    else:
        rx = re.compile(check.pattern or "")
        for target in check.targets:
            for f in iter_files([target]):
                for n, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                    if rx.search(line):
                        hits.append(f"{f.relative_to(REPO).as_posix()}:{n}")
    return hits


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--strict", action="store_true", help="exit 1 if any check fails")
    args = ap.parse_args()

    failed = 0
    for c in CHECKS:
        hits = run(c)
        status = "PASS" if not hits else "FAIL"
        failed += bool(hits)
        print(f"[{status}] {c.name}  ({c.ruling})")
        if hits:
            print(f"       why: {c.why}")
            for h in hits[:8]:
                print(f"       - {h}")
            if len(hits) > 8:
                print(f"       ... and {len(hits) - 8} more")
    print("")
    print(f"{len(CHECKS) - failed} passing, {failed} failing")
    return 1 if (args.strict and failed) else 0


if __name__ == "__main__":
    sys.exit(main())
