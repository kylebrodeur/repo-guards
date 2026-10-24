"""The prose gate: banned characters/words in tracked markdown.

Fail-closed: findings are evidence; fix the prose, never weaken the
list. Reports file:line + the matched term.
"""

from __future__ import annotations

import re
from pathlib import Path

from .config import CheckResult, Config, _run


def check(repo: Path, cfg: Config) -> CheckResult:
    findings: list[str] = []
    out = _run(repo, ["git", "ls-files", "*.md"], check=False)
    tracked = [line for line in out.splitlines() if line.strip()]
    skip = tuple(re.compile(p) for p in cfg.prose_skip_patterns)
    for rel in tracked:
        path = repo / rel
        try:
            text = path.read_text()
        except (OSError, UnicodeDecodeError):
            continue
        for i, line in enumerate(text.splitlines(), 1):
            # rule-citation lines (documents that NAME the banned words as
            # their own rule) are definitions, not violations:
            if any(pattern.search(line) for pattern in skip):
                continue
            for term in cfg.prose_banned:
                if term in line:
                    findings.append(f"{rel}:{i}: {term!r}")
    return CheckResult(ok=not findings, findings=tuple(findings[:50]))
