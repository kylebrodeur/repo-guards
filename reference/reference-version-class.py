#!/usr/bin/env python3
"""Release version-class guard (PRIVATE system tooling).

Rule (Kyle, 2026-10-14): a release whose content changes are DOCS ONLY
(guide copies synced from private sources, release notes, README wording,
comments) must be a PATCH-level bump of the last released tag (e.g. v1.3.1
after v1.3.0), and release-repo.sh must refuse a minor/major bump for it.
Anything carrying code (toolkit/*.py, server/*, pyproject deps, tests,
workflows) may bump minor or major.

Usage: version-class.py <repo> <version>
Exit 0 when the requested version is legal for the pending changes,
exit 1 with the reason otherwise. Run BEFORE the squash (the diff is
origin/main..HEAD pre-squash, or the working tree when dirty).
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

SYSTEM = Path(__file__).resolve().parent.parent.parent

# Paths whose changes count as DOCS-ONLY. Everything else is CODE.
DOC_PATHS = (
    "docs/",
    "README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "FUNDING.yml",
    "AGENTS.suggested.md",
    "llms.txt",
    ".github/ISSUE_TEMPLATE/",
)

SEMVER = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


def diff_files(repo: Path) -> list[str]:
    """Changed paths between the last release tag and HEAD, plus dirty worktree paths."""
    tags = subprocess.run(
        ["git", "-C", str(repo), "tag", "--sort=-creatordate"], capture_output=True, text=True
    ).stdout.split()
    released = [t for t in tags if SEMVER.match(t)]
    if not released:
        out = subprocess.run(
            ["git", "-C", str(repo), "status", "--porcelain"], capture_output=True, text=True
        ).stdout.splitlines()
        return [line[3:].strip() for line in out if line.strip()]
    out = subprocess.run(
        ["git", "-C", str(repo), "diff", "--name-only", f"{released[0]}...HEAD"],
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    out.extend(
        line[3:].strip()
        for line in subprocess.run(
            ["git", "-C", str(repo), "status", "--porcelain"], capture_output=True, text=True
        ).stdout.splitlines()
        if line.strip()
    )
    return [line for line in out if line.strip()]


def is_docs_only(files: list[str]) -> bool:
    # An empty diff counts docs-only: a patch re-cut (docs/re-notes) stays
    # legal; a minor/major with NO changes is refused as pointless.
    return all(f.startswith(DOC_PATHS) for f in files)


def _diff_hunks(repo: Path, base: str) -> list[str]:
    """Unified-diff hunks vs base (committed + worktree) for the neutrality check."""
    out = subprocess.run(
        ["git", "-C", str(repo), "diff", f"{base}...HEAD", "--", "pyproject.toml", "uv.lock"],
        capture_output=True,
        text=True,
    ).stdout
    out += subprocess.run(
        ["git", "-C", str(repo), "diff", "HEAD", "--", "pyproject.toml", "uv.lock"],  # staged + unstaged
        capture_output=True,
        text=True,
    ).stdout
    return [line for line in out.splitlines() if line and line[0] in "+-" and not line.startswith(("+++", "---"))]


def version_line_only(repo: Path, base: str) -> bool:
    """True when EVERY +/- line touching pyproject/uv.lock is a version line
    (the release bump itself): bookkeeping, never a code change. uv.lock's
    `version = "x.y.z"` package-entry lines count; `[[package]]` blocks and
    dependency lines do not."""
    for line in _diff_hunks(repo, base):
        body = line.lstrip("+-").strip()
        if body.startswith('version = "') or body.startswith("version = '"):
            continue
        return False
    return True


def bump_kind(version: str) -> tuple[int, int, int] | None:
    m = SEMVER.match(version.strip().lstrip("v"))
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 1
    repo, version = SYSTEM / argv[0], argv[1]
    if not repo.is_dir():
        print(f"version-class: {repo} is not a repo here", file=sys.stderr)
        return 1
    requested = bump_kind(version)
    if requested is None:
        print(f"version-class: {version!r} is not a semver tag", file=sys.stderr)
        return 1

    tags = subprocess.run(
        ["git", "-C", str(repo), "tag", "--sort=-creatordate"], capture_output=True, text=True
    ).stdout.split()
    released = [t for t in tags if SEMVER.match(t)]
    if not released:
        return 0  # first release: free choice
    last = bump_kind(released[0])
    assert last is not None
    if requested <= last:
        print(f"version-class: {version} is not newer than the last release ({released[0]})", file=sys.stderr)
        return 1

    files = diff_files(repo)
    neutral = (
        version_line_only(repo, released[0])
        if any(f.startswith(("pyproject.toml", "uv.lock")) for f in files)
        else False
    )
    if neutral:
        # drop the bookkeeping files from the docs/code classification
        files = [f for f in files if not f.startswith(("pyproject.toml", "uv.lock"))]
    if is_docs_only(files) and (requested[1] != last[1] or requested[0] != last[0]):
        print(
            f"version-class: DOCS-ONLY release must be a PATCH bump: last is {released[0]}, "
            f"requested {version} moves minor/major. Rule (2026-10-14): doc-only updates = patch. "
            f"Docs changed: {', '.join(files[:5]) or '(version bump only)'}{' ...' if len(files) > 5 else ''}",
            file=sys.stderr,
        )
        return 1
    state = "docs-only -> patch required" if is_docs_only(files) else "code changes present"
    print(f"version-class: ok ({state}{' + version-bump bookkeeping (neutral)' if neutral else ''}, {version})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
