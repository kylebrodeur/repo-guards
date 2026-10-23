"""The version-class guard: content class pins the bump class.

A release whose changed paths (last tag..HEAD + the dirty worktree) are
ALL in the docs set must be a PATCH bump. Code may bump minor or major.
Run BEFORE the squash/tag; exit 1 with the reason otherwise.

Pure here: changed-files detection is injected so tests can drive it
without fixtures.
"""

from __future__ import annotations

from pathlib import Path

from .config import SEMVER, CheckResult, Config, _run, latest_tag

CODE_EXTENSIONS = frozenset({".py", ".toml", ".lock", ".ts", ".js", ".sh"})


def _is_docs(path: str, docs_paths: tuple[str, ...]) -> bool:
    """A path is docs when it matches a docs pattern and is not code-shaped.

    Two-tier matching (the wave's real bug encoded): an EXACT-file entry
    always wins (a repo may declare a .yml file docs); a DIR-prefix entry
    never swallows code-extension files (a .py under docs/ is a generator
    script, not docs).
    """
    for pattern in docs_paths:
        if not pattern.endswith("/") and (path == pattern or path.startswith(pattern + "/")):
            return True
    if Path(path).suffix in CODE_EXTENSIONS:
        return False
    for pattern in docs_paths:
        if pattern.endswith("/") and path.startswith(pattern):
            return True
    return False


def changed_files(cwd: Path, cfg: Config) -> list[str]:
    """Changed paths between the latest tag and HEAD, plus dirty worktree paths."""
    files: list[str] = []
    last = latest_tag(cwd)
    if last:
        out = _run(cwd, ["git", "diff", "--name-only", f"{last}..HEAD"], check=False)
        files += [line for line in out.splitlines() if line.strip()]
    out = _run(cwd, ["git", "status", "--porcelain"], check=False)
    for line in out.splitlines():
        if line.strip():
            files.append(line[3:].strip().strip('"'))
    return files


def check(
    repo: Path, cfg: Config, requested: str, files: list[str] | None = None, last: str | None = None
) -> CheckResult:
    match = SEMVER.fullmatch(requested)
    if not match:
        return CheckResult(ok=False, findings=(f"{requested!r} is not a valid vX.Y.Z",))
    major, minor, _patch = (int(match.group(i)) for i in (1, 2, 3))

    real = files if files is not None else changed_files(repo, cfg)
    code = [p for p in real if not _is_docs(p, cfg.docs_paths)]

    last = last or latest_tag(repo)
    if last:
        lm = SEMVER.fullmatch(last)
        if lm:
            last_major, last_minor = int(lm.group(1)), int(lm.group(2))
            req_major, req_minor = major, minor
            if code:
                # code changes: a strictly increasing version
                if (req_major, req_minor) < (last_major, last_minor):
                    return CheckResult(ok=False, findings=(f"{requested} decreases {last} with code changes",))
                if (req_major, req_minor) == (last_major, last_minor) and not _patch_gt(requested, last):
                    return CheckResult(ok=False, findings=(f"{requested} does not increase {last} for a code release",))
            else:
                # docs-only: patch only (same major.minor, bigger patch)
                if (req_major, req_minor) != (last_major, last_minor):
                    return CheckResult(
                        ok=False,
                        findings=(
                            f"docs-only content ({len(real)} files) but {requested} changes major.minor "
                            f"(last {last}): PATCH bump only",
                        ),
                    )
    return CheckResult(ok=True)


def _patch_gt(requested: str, last: str) -> bool:
    a = [int(x) for x in requested.lstrip("v").split(".")]
    b = [int(x) for x in last.lstrip("v").split(".")]
    return a > b
