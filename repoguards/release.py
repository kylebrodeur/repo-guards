"""The release flow: gates -> notes check -> bump -> tag -> gh release -> parity.

Usage (library): release.plan(repo, cfg, version) -> list of plan steps
(executed by the CLI); release.run(repo, cfg, version, dry_run=True).
The flow refuses to proceed on any gate failure: nothing is tagged red.
"""

from __future__ import annotations

from pathlib import Path

from . import ci as ci_guard
from . import lockfile_parity, parity, prose, version_class
from .config import CheckResult, Config, _run


def gates(repo: Path, cfg: Config, version: str) -> list[CheckResult]:
    """The gate battery, in the fixed order. Each result names its guard."""
    results = [
        ("docs-gate: prose", prose.check(repo, cfg)),
        ("gate: version-class", version_class.check(repo, cfg, version)),
        ("gate: lockfile-parity", lockfile_parity.check(repo, cfg)),
        ("gate: ci-verbatim", ci_guard.check(repo, cfg)),
    ]
    return results


def notes_path(repo: Path, cfg: Config, version: str) -> Path | None:
    base = repo / cfg.notes_dir
    for candidate in (base, *[base / f for f in _slug_candidates(cfg)]):
        path = candidate / cfg.notes_glob.format(tag=version)
        if path.is_file():
            return path
    return None


def _slug_candidates(cfg: Config) -> list[str]:
    """Slug spellings to try under notes_dir: the repo name, then the
    repo name with a configured prefix peeled and a configured suffix
    peeled, re-composed both ways, then the explicit extras.

    The prefix and the suffix are CONFIG, and not a hardcoded family's
    naming convention. A family whose repos are named
    ``<prefix>-<core>-<suffix>`` sets them; a family whose repos are
    named plainly sets neither, and the repo name is the only
    candidate.
    """
    candidates = [cfg.repo]
    core = cfg.repo
    if cfg.repo_prefix:
        core = core.removeprefix(cfg.repo_prefix)
    if cfg.repo_suffix:
        core = core.removesuffix(cfg.repo_suffix)
    for prefix in (cfg.repo_prefix, ""):
        for suffix in ("", cfg.repo_suffix):
            if not prefix and not suffix:
                continue
            candidate = f"{prefix}{core}{suffix}"
            if candidate not in candidates:
                candidates.append(candidate)
    # The fully peeled core, so a family whose notes live under the
    # bare core are found too.
    if core and core not in candidates:
        candidates.append(core)
    extras = [c for c in cfg.notes_candidates if c not in candidates]
    return candidates + extras


def run(repo: Path, cfg: Config, version: str, *, dry_run: bool = True, yes: bool = False) -> bool:
    """The flow. Returns ok. Refuses before any write on a failed gate."""
    for name, result in gates(repo, cfg, version):
        if not result:
            print(f"REFUSED at {name}:")
            for f in result.findings:
                print(f"  - {f}")
            return False

    notes = notes_path(repo, cfg, version)
    if notes is None:
        print(
            f"REFUSED: source notes missing ({cfg.notes_dir}/<slug>/"
            f"{cfg.notes_glob.format(tag=version)}): write notes FIRST"
        )
        return False

    tag = version if cfg.require_v_prefix and not version.startswith("v") else version
    print("== gates ok")
    print(f"== tag: {tag} at HEAD ({_run(repo, ['git', 'rev-parse', '--short', 'HEAD']).strip()})")
    print(f"== release notes source: {notes.relative_to(repo)}")
    if dry_run:
        print("== dry run: stopping before the write")
        return True

    _run(repo, ["git", "tag", "-a", tag, "-m", f"{cfg.repo} {tag}"])
    _run(repo, ["git", "push", "origin", tag])
    _run(
        repo,
        [
            "gh",
            "release",
            "create",
            tag,
            "--repo",
            f"{cfg.owner}/{cfg.repo}",
            "--notes-file",
            str(notes),
            "--title",
            f"{cfg.repo} {tag}",
        ],
    )
    verdict = parity.check(repo, cfg)
    if not verdict:
        print("NOT PUBLISHED (parity failed after the push):")
        for f in verdict.findings:
            print(f"  - {f}")
        return False
    print(f"== published: {cfg.owner}/{cfg.repo} {tag} (parity ok)")
    return True
