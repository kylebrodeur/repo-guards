"""The lockfile-parity guard: self-version consistency.

Every lockfile's record of its OWN project version must match its
pyproject (uv.lock's [[package]] for the project's name vs pyproject's
version). A release whose lock lags is a wrong published state; this
guard runs with parity checks before any tag.

Also: when version files exist in MULTIPLE project dirs (multiproject
layouts), every one must agree.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from .config import CheckResult, Config


def _self_versions(repo: Path, cfg: Config) -> dict[str, tuple[str | None, str | None]]:
    """Per version-file dir: (pyproject version, lockfile self-version)."""
    out: dict[str, tuple[str | None, str | None]] = {}
    for rel in cfg.version_files:
        proj = (repo / rel).parent
        pyproject = proj / "pyproject.toml"
        if not pyproject.is_file():
            continue
        data = tomllib.loads(pyproject.read_text())
        name = (data.get("project") or {}).get("name")
        version = (data.get("project") or {}).get("version")
        lock_version: str | None = None
        for lock_name in ("uv.lock",):
            lock = proj / lock_name
            if not lock.is_file() or not name:
                continue
            text = lock.read_text()
            pattern = re.compile(r'\[\[package\]\]\s*\nname = "' + re.escape(str(name)) + r'"\s*\nversion = "([^"]+)"')
            if match := pattern.search(text):
                lock_version = match.group(1)
        out[str(proj.relative_to(repo)) or "."] = (
            str(version) if version else None,
            lock_version,
        )
    return out


def check(repo: Path, cfg: Config) -> CheckResult:
    findings: list[str] = []
    versions = _self_versions(repo, cfg)
    distinct = {v for pair in versions.values() for v in pair if v}
    if len(distinct) > 1:
        findings.append(f"version files disagree: {sorted(distinct)}")
    for proj, (py_version, lock_version) in versions.items():
        if py_version and lock_version and py_version != lock_version:
            findings.append(
                f"{proj}: lockfile self-version {lock_version} != pyproject {py_version} (fix: uv lock in {proj})"
            )
        if py_version is None:
            findings.append(f"{proj}: no [project].version (not releasable)")
    # NOTE: the version-vs-tag check lives in the PARITY guard (post-release
    # state); pre-release bumps legitimately sit above the last tag.
    return CheckResult(ok=not findings, findings=tuple(findings))
