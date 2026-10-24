"""Fixture: a synthetic git repo with a tag, a release-notes file, and version files."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

_GIT = shutil.which("git") or "/opt/homebrew/bin/git"


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    repo = tmp_path / "myrepo"
    repo.mkdir()

    def run(*args: str, check: bool = True):
        """git with an ABSOLUTE path: a name lookup inside some pytest/uv
        spawn environments can miss the brew git even with a healthy
        parent PATH (observed live in this kit's first session)."""
        if args and args[0] == "git":
            args = (_GIT, *args[1:])
        return subprocess.run(args, cwd=str(repo), capture_output=True, text=True, check=check)

    run("git", "init", "-q", "-b", "main")
    run("git", "config", "user.email", "test@example.com")
    run("git", "config", "user.name", "test")
    (repo / "pyproject.toml").write_text('[project]\nname = "myrepo"\nversion = "0.1.0"\n')
    (repo / "uv.lock").write_text('[[package]]\nname = "myrepo"\nversion = "0.1.0"\n')
    (repo / "README.md").write_text("# myrepo\nplain readme text\n")
    (repo / "src.py").write_text("x = 1\n")
    # release notes under the default notes dir:
    notes = repo / "docs" / "releases" / "myrepo"
    notes.mkdir(parents=True)
    (notes / "RELEASE-NOTES-v0.1.1.md").write_text(
        "# myrepo v0.1.1\n\nReleased now. Real notes body over forty characters to pass the length check.\n"
    )
    (repo / ".repolice.toml").write_text('owner = "someone"\nrepo = "myrepo"\nversion_files = ["pyproject.toml"]\n')
    run("git", "add", "-A")
    run("git", "commit", "-q", "-m", "feat: init with config")
    # tag AFTER everything so HEAD == tag (the parity happy path):
    run("git", "tag", "v0.1.0")
    return repo
