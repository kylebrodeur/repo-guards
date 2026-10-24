"""repo-guards: repo-discipline guards driven by one TOML config per repo.

The config file (default `.repolice.toml` at the repo root... name TBD by
the kit's README; the loader accepts any passed path) declares:

    owner = "you"                      # GitHub owner for gh calls
    repo = "repo-name"                 # GitHub repo name (default: dir name)
    notes_dir = "docs/releases"        # where source notes live
    notes_glob = "RELEASE-NOTES-{tag}.md"
    version_files = ["pyproject.toml", "server/pyproject.toml"]
    require_v_prefix = true
    docs_paths = [...]                 # for version-class
    prose_banned = ["-", "-", ...]     # chars/words
    ci = ["uv run pytest tests -q"]    # the verbatim CI commands

Every guard is a pure function over (repo_path, config) returning
CheckResult(ok, findings). The CLI wraps them: `guards check <repo>`,
`release <repo> <version>`.

This file's rules come from the guard-patterns doc: releases need an
oracle; content class pins bump class; one rewrite per transformation.
"""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - py310 fallback
    import tomli as tomllib  # type: ignore[no-redef]

DEFAULT_CONFIG_NAMES = (".repolice.toml", "repolice.toml")
SEMVER = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")

DEFAULT_DOCS_PATHS = (
    "docs/",
    "README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "FUNDING.yml",
    "SUPPORT.md",
    "CODE_OF_CONDUCT.md",
    "AGENTS.suggested.md",
    "llms.txt",
    ".github/ISSUE_TEMPLATE/",
    ".github/PULL_REQUEST_TEMPLATE.md",
)


@dataclass(frozen=True)
class CheckResult:
    ok: bool
    findings: tuple[str, ...] = ()

    def __bool__(self) -> bool:
        return self.ok


@dataclass
class Config:
    owner: str
    repo: str
    notes_dir: str = "docs/releases"
    notes_glob: str = "RELEASE-NOTES-{tag}.md"
    version_files: tuple[str, ...] = ("pyproject.toml",)
    require_v_prefix: bool = True
    docs_paths: tuple[str, ...] = DEFAULT_DOCS_PATHS
    prose_banned: tuple[str, ...] = ("\u2014", "\u2013", "\u2212", "robust", "leverage", "seamlessly", "utilize")
    prose_skip_patterns: tuple[str, ...] = (
        r"no .*slop|banned|must not use|forbidden",
        r"^\(robust / leverage",
    )
    ci: tuple[str, ...] = ()
    squash: str | None = None  # None (default no-squash), "always", or never
    notes_candidates: tuple[str, ...] = ()  # extra slug spellings to find notes under
    # The prefix and suffix a family's repo names carry, if any. A
    # family whose repos are named "<prefix>-<core>-<suffix>" sets
    # them, and the notes under a different spelling are then found.
    # A family whose repos are named plainly sets neither.
    repo_prefix: str = ""
    repo_suffix: str = ""

    @classmethod
    def load(cls, repo: Path, path: Path | None = None) -> "Config":
        if path is None:
            env_path = os.environ.get("REPOLICE_CONFIG", "").strip()
            if env_path:
                path = Path(env_path)
                if not path.is_file():
                    raise FileNotFoundError(f"REPOLICE_CONFIG names a missing file: {path}")
        if path is None:
            for name in DEFAULT_CONFIG_NAMES:
                candidate = repo / name
                if candidate.is_file():
                    path = candidate
                    break
        if path is None:
            raise FileNotFoundError(f"no config ({', '.join(DEFAULT_CONFIG_NAMES)}) in {repo}")
        data = tomllib.loads(path.read_text())
        owner = str(data.get("owner") or "").strip()
        if not owner:
            # derive from the git remote, `github.com/<owner>/<repo>.git`:
            remote = _run(repo, ["git", "remote", "get-url", "origin"], check=False)
            match = re.search(r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/.]+)", remote)
            if not match:
                raise ValueError("config: owner unset and origin remote does not name a GitHub owner")
            owner = match["owner"]
        cfg = cls(
            owner=owner,
            repo=str(data.get("repo") or match.group("repo")),
            notes_dir=str(data.get("notes_dir") or cls.notes_dir),
            notes_glob=str(data.get("notes_glob") or cls.notes_glob),
            version_files=tuple(data.get("version_files") or cls.version_files),
            require_v_prefix=bool(data.get("require_v_prefix", cls.require_v_prefix)),
            docs_paths=tuple(data.get("docs_paths") or cls.docs_paths),
            prose_banned=tuple(data.get("prose_banned") or cls.prose_banned),
            prose_skip_patterns=tuple(data.get("prose_skip_patterns") or cls.prose_skip_patterns),
            ci=tuple(data.get("ci") or ()),
            squash=data.get("squash"),
            notes_candidates=tuple(data.get("notes_candidates") or ()),
            repo_prefix=str(data.get("repo_prefix") or ""),
            repo_suffix=str(data.get("repo_suffix") or ""),
        )
        return cfg


def _run(cwd: Path, args: list[str], check: bool = True) -> str:
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise RuntimeError(f"{args[0]} failed: {result.stderr.strip()[:200]}")
    return result.stdout


def latest_tag(cwd: Path) -> str | None:
    """The newest release tag by creatordate (NOT v-preferred: a newer
    non-v tag is still latest - the parity guard flags the prefix)."""
    out = _run(cwd, ["git", "tag", "--sort=-creatordate"], check=False)
    tags = [t for t in out.splitlines() if SEMVER.fullmatch(t)]
    return tags[0] if tags else None


def tag_tip(cwd: Path, tag: str) -> bool:
    """True when the tag resolves to the CURRENT HEAD commit."""
    tagged = _run(cwd, ["git", "rev-parse", f"{tag}^{{commit}}"], check=False).strip()
    head = _run(cwd, ["git", "rev-parse", "HEAD"], check=False).strip()
    return tagged == head and bool(tagged)


def version_on_disk(repo: Path, cfg: Config) -> str | None:
    """The first resolvable version across the configured version files."""
    import tomllib

    for rel in cfg.version_files:
        path = repo / rel
        if not path.is_file():
            continue
        data = tomllib.loads(path.read_text())
        version = (data.get("project") or {}).get("version")
        if version:
            return str(version)
    return None
