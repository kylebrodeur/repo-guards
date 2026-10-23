"""The prose gate's contract."""

from __future__ import annotations

import subprocess
from pathlib import Path

from repoguards import prose
from repoguards.config import Config


def test_banned_dash_reported_with_location(repo: Path):
    (repo / "guide.md").write_text("This line has a \u2014 real em dash.\n")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    cfg = Config(owner="o", repo="myrepo")
    result = prose.check(repo, cfg)
    assert any("guide.md:1" in f for f in result.findings)


def test_banned_word_reported(repo: Path):
    (repo / "readme2.md").write_text("This is a robust solution.\n")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    cfg = Config(owner="o", repo="myrepo")
    result = prose.check(repo, cfg)
    assert any("'robust'" in f for f in result.findings)


def test_clean_repo_passes(repo: Path):
    (repo / "clean.md").write_text("Plain english only, with hyphens - wait, that is banned.\n")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    cfg = Config(owner="o", repo="myrepo", prose_banned=("robust",))
    assert prose.check(repo, cfg).ok


def test_only_first_fifty_findings(repo: Path):
    lines = "\n".join(f"line with a dash - {i}" for i in range(80))
    (repo / "many.md").write_text(lines + "\n")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    cfg = Config(owner="o", repo="myrepo")
    result = prose.check(repo, cfg)
    assert len(result.findings) <= 50
