"""The release-parity guard: "published" is a testable state.

For the repo's latest release tag, ALL must hold:
(a) the tag is pushed to the remote (its sha matches the local tag object
    peel - read via ls-remote, so temp clones work without fetches) AND
    the tag's commit is on the remote default branch (an ancestor), or
    the remote branch ref is unavailable (empty repo edge) and only the
    push check holds,
(b) a GitHub release object exists with a real notes body,
(c) a source notes file exists under {notes_dir}/{slug}/{notes_glob},
(d) the version on disk (across version_files) equals the tag.
Optionally (e) the info-note when the tag is not at HEAD.

Exit 1 = do not claim published.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from .config import CheckResult, Config, _run, latest_tag, tag_tip, version_on_disk


def check(repo: Path, cfg: Config) -> CheckResult:
    findings: list[str] = []
    tag = latest_tag(repo)
    if tag is None:
        return CheckResult(ok=False, findings=(f"{repo.name}: no release tags at all",))
    if cfg.require_v_prefix and not tag.startswith("v"):
        findings.append(f"{repo.name}: latest tag {tag!r} is not v-prefixed")

    # (a) the tag on the remote:
    # local comparison peels the annotated tag (rev-parse TAG^{} = the
    # commit); ls-remote's ^{} peel already returns the commit sha:
    local_sha = _run(repo, ["git", "rev-parse", tag + "^{}"], check=False).strip()
    remote = _run(
        repo,
        [
            "git",
            "ls-remote",
            f"https://github.com/{cfg.owner}/{cfg.repo}.git",
            "refs/tags/" + tag,
            "refs/tags/" + tag + "^{}",
            "refs/heads/main",
        ],
        check=False,
    )
    tag_remote: str | None = None
    main_remote: str | None = None
    for line in remote.splitlines():
        if not line.strip():
            continue
        sha, ref = line.split(maxsplit=1)
        if ref.startswith("refs/heads/"):
            main_remote = sha
        elif ref.endswith("^{}"):  # annotated tag peel = the commit sha
            tag_remote = sha
    if not local_sha:
        findings.append(f"{repo.name}: tag {tag} missing locally")
    elif not tag_remote:
        findings.append(f"{repo.name}: tag {tag} is not pushed to origin (push it: git push origin {tag})")
    elif tag_remote != local_sha:
        findings.append(
            f"{repo.name}: remote tag {tag} ({tag_remote[:12]}) != local ({local_sha[:12]}): "
            "re-pointed locally but not force-pushed"
        )
    elif main_remote and not _ancestor_tag(repo, tag_remote, main_remote):
        findings.append(f"{repo.name}: tag {tag} is NOT on origin/main")

    # (b) GH release with a real body:
    body = _run(
        repo,
        ["gh", "release", "view", tag, "--repo", f"{cfg.owner}/{cfg.repo}", "--json", "body", "--jq", ".body"],
        check=False,
    )
    if body.strip() in ("", "null") or "Not Found" in body:
        findings.append(
            f"{repo.name}: tag {tag} exists but NO GitHub release - gh release create {tag} --notes-file ..."
        )
    elif len(body.strip()) <= 40:
        findings.append(f"{repo.name}: release {tag} has no real notes body (<= 40 chars)")

    # (c) source notes file:
    if _find_notes(repo, cfg, tag) is None:
        findings.append(
            f"{repo.name}: no source notes at {cfg.notes_dir}/<slug>/"
            f"{cfg.notes_glob.format(tag=tag)} (write notes first)"
        )

    # (d) version parity on disk:
    disk = version_on_disk(repo, cfg)
    if disk is None:
        findings.append(f"{repo.name}: no resolvable version across {cfg.version_files}")
    elif disk.lstrip("v") != tag.lstrip("v"):
        findings.append(f"{repo.name}: version on disk ({disk}) != tag ({tag})")

    # (e) informational: the tag is at the working tip. Commits beyond a
    # tag are normal iteration: the note rides the output but `ok` is
    # decided only by the real findings above.
    ok = not findings
    if not tag_tip(repo, tag):
        findings.append(f"{repo.name}: (note) tag {tag} is NOT at HEAD (there are commits beyond it)")
    return CheckResult(ok=ok, findings=tuple(findings))


def _ancestor_tag(repo: Path, tag_sha: str, main_sha: str) -> bool:
    """True when the tag's commit is an ancestor of main's commit (or equal)."""
    if tag_sha == main_sha:
        return True
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", tag_sha, main_sha],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _find_notes(repo: Path, cfg: Config, tag: str) -> Path | None:
    base = repo / cfg.notes_dir
    if not base.is_dir():
        return None
    wanted = cfg.notes_glob.format(tag=tag)
    direct = base / wanted
    if direct.is_file():
        return direct
    # slug subdirs (the docs/releases/<slug>/ spelling):
    for child in sorted(base.iterdir()):
        if child.is_dir() and (child / wanted).is_file():
            return child / wanted
    return None
