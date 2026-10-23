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
RUNTIME_SCOPE = ["apps/app/src", "backends/agent-runtime/app"]
COPY_SCOPE = ["apps/app/src/copy", "apps/app/src/components", "apps/app/src/routes"]
SKIP = re.compile(r"\.(test|stories)\.[jt]sx?$|/node_modules/|\.stories\.")


@dataclass
class Check:
    name: str
    ruling: str
    why: str
    kind: str  # "absent" = these paths must not exist; "forbid" = this regex must not appear
    targets: list[str]
    pattern: str | None = None


CHECKS = [
    Check(
        "no /keep or /plan-purchase routes",
        "decisions.md §34",
        "Kyle: never add the /keep route back in; plan-purchase is scrubbed.",
        "absent",
        ["apps/app/src/routes/keep*", "apps/app/src/routes/**/plan-purchase*"],
    ),
    Check(
        "no legacy plantnet/bioclip identify routes",
        "decisions.md §37",
        "Kyle: there is no /plantnet route; all identification goes through /identify. "
        "Note: api/agent/identify.ts is the live gateway and is NOT on this list.",
        "absent",
        ["apps/app/src/routes/api/identify/plantnet.ts", "apps/app/src/routes/api/identify/bioclip.ts"],
    ),
    Check(
        "workflow discipline (no ad-hoc Actions; deploy-agent-runtime present)",
        "AGENTS.md deploy law (Kyle 2026-10-16 correction)",
        "No ad-hoc/random Actions workflows; the sanctioned runtime-deploy "
        "workflow MUST exist (runtime deploys are cloud-only via WIF now).",
        "require",
        [".github/workflows/deploy-agent-runtime.yml"],
    ),
    Check(
        "no @/lib/db imports in runtime code",
        "LEARNINGS.md (auth, observability, dead code)",
        "@/lib/db is inert; any runtime import is a defect.",
        "forbid",
        RUNTIME_SCOPE,
        r"from\s+['\"]@/lib/db['\"]",
    ),
    Check(
        "no Grok or xAI references in runtime code",
        "decisions.md §33 (Kyle, 2026-09-16)",
        "No Grok or xAI in the final product. Word boundaries avoid 'Vertex AI'.",
        "forbid",
        RUNTIME_SCOPE,
        r"(?i)\b(grok|xai)\b|\bx\.ai\b|\bx ai\b",
    ),
    Check(
        "no 'hosted credit' wording in user copy",
        "decisions.md §36 (Kyle, 2026-10-09)",
        "Say 'Credits' or 'ID credits'. 'Hosted Credits' is retired.",
        "forbid",
        COPY_SCOPE,
        r"(?i)hosted[ -]credit",
    ),
    Check(
        "no cut tier names in user copy",
        "decisions.md §35 (Kyle, 2026-10-11)",
        "One Founder plan plus credit packs. Keep, Lifetime, and Founder Pro are cut.",
        "forbid",
        ["apps/app/src/copy"],
        r"(?i)founder pro|lifetime plan|\bkeep plan\b",
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
    exist — Kyle's 2026-10-16 workflow law), ``forbid`` (regex must not
    appear inside the target scope).
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
