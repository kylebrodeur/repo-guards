"""The lockfile-parity contract."""

from __future__ import annotations

from pathlib import Path

from repoguards import lockfile_parity
from repoguards.config import Config


def test_lock_lag_reported(repo: Path):
    (repo / "pyproject.toml").write_text('[project]\nname = "myrepo"\nversion = "0.2.0"\n')
    # uv.lock still says 0.1.0:
    cfg = Config(owner="o", repo="myrepo", version_files=("pyproject.toml",))
    result = lockfile_parity.check(repo, cfg)
    assert not result
    assert any("lockfile self-version 0.1.0 != pyproject 0.2.0" in f for f in result.findings)


def test_lock_synced_ok(repo: Path):
    (repo / "pyproject.toml").write_text('[project]\nname = "myrepo"\nversion = "0.2.0"\n')
    (repo / "uv.lock").write_text('[[package]]\nname = "myrepo"\nversion = "0.2.0"\n')
    cfg = Config(owner="o", repo="myrepo", version_files=("pyproject.toml",))
    assert lockfile_parity.check(repo, cfg).ok


def test_multiproject_disagreement_reported(repo: Path):
    (repo / "server").mkdir()
    (repo / "server" / "pyproject.toml").write_text('[project]\nname = "myrepo-server"\nversion = "0.3.0"\n')
    (repo / "server" / "uv.lock").write_text('[[package]]\nname = "myrepo-server"\nversion = "0.3.0"\n')
    cfg = Config(owner="o", repo="myrepo", version_files=("pyproject.toml", "server/pyproject.toml"))
    result = lockfile_parity.check(repo, cfg)
    text = "\n".join(result.findings)
    assert "version files disagree" in text  # root 0.1.0(+lock) vs server 0.3.0


def test_multiproject_one_lag_reported(repo: Path):
    (repo / "server").mkdir()
    (repo / "server" / "pyproject.toml").write_text('[project]\nname = "myrepo-server"\nversion = "0.1.0"\n')
    (repo / "server" / "uv.lock").write_text('[[package]]\nname = "myrepo-server"\nversion = "0.3.0"\n')
    cfg = Config(owner="o", repo="myrepo", version_files=("pyproject.toml", "server/pyproject.toml"))
    result = lockfile_parity.check(repo, cfg)
    text = "\n".join(result.findings)
    assert "server: lockfile self-version 0.3.0 != pyproject 0.1.0" in text


def test_multiproject_all_synced_ok(repo: Path):
    (repo / "server").mkdir()
    (repo / "server" / "pyproject.toml").write_text('[project]\nname = "myrepo-server"\nversion = "0.1.0"\n')
    (repo / "server" / "uv.lock").write_text('[[package]]\nname = "myrepo-server"\nversion = "0.1.0"\n')
    cfg = Config(owner="o", repo="myrepo", version_files=("pyproject.toml", "server/pyproject.toml"))
    assert lockfile_parity.check(repo, cfg).ok


def test_no_project_version_reported(repo: Path):
    (repo / "pyproject.toml").write_text('[project]\nname = "myrepo"\n')
    cfg = Config(owner="o", repo="myrepo", version_files=("pyproject.toml",))
    result = lockfile_parity.check(repo, cfg)
    assert any("no [project].version" in f for f in result.findings)
