"""The CI-verbatim guard: run the repo's own CI commands, record results.

Not "similar" commands: the config's `ci` list is the contract (it should
mirror .github/workflows/ci.yml). A guard (not a convenience) because a
red repo must not be released; the release flow calls check() and stops.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from .config import CheckResult, Config


def check(repo: Path, cfg: Config) -> CheckResult:
    if not cfg.ci:
        return CheckResult(
            ok=False, findings=("no `ci` commands in the config (add them; mirror .github/workflows/ci.yml)",)
        )
    findings: list[str] = []
    for command in cfg.ci:
        result = subprocess.run(command, shell=True, cwd=repo, capture_output=True, text=True, timeout=900)
        if result.returncode != 0:
            tail = (result.stdout + result.stderr).strip().splitlines()
            findings.append(f"CI FAILED: {command}\n    " + "\n    ".join(tail[-5:]))
    return CheckResult(ok=not findings, findings=tuple(findings))


def run(repo: Path, cfg: Config) -> CheckResult:
    """Back-compat alias."""
    return check(repo, cfg)
