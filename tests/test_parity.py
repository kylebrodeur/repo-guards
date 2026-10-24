"""The parity guard's contract, driven by a synthetic repo (no gh: the
GitHub-facing checks are exercised via the fake runner where needed; here
the pure-local checks dominate)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from repoguards import parity
from repoguards.config import Config, latest_tag, tag_tip, version_on_disk


def test_latest_tag_prefers_v_prefixed(repo: Path):
    assert latest_tag(repo) == "v0.1.0"


def test_tag_tip_true_at_head(repo: Path):
    assert tag_tip(repo, "v0.1.0") is True


def test_tag_tip_false_when_beyond(repo: Path):
    (repo / "new.py").write_text("y = 2\n")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-q", "-m", "feat: beyond"], cwd=repo, check=True, capture_output=True)
    assert tag_tip(repo, "v0.1.0") is False


def test_version_on_disk_single(repo: Path):
    cfg = Config.load(repo)
    assert version_on_disk(repo, cfg) == "0.1.0"


def test_config_derives_owner_from_remote(repo: Path):
    subprocess.run(
        ["git", "remote", "add", "origin", "https://github.com/someone/myrepo.git"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    cfg = Config.load(repo)  # config file has owner; but drop it to test derivation:
    cfg_path = repo / ".repolice.toml"
    cfg_path.write_text('repo = "myrepo"\nversion_files = ["pyproject.toml"]\n')
    cfg = Config.load(repo)
    assert cfg.owner == "someone"


def test_config_missing_refuses(tmp_path: Path):
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(FileNotFoundError):
        Config.load(empty)


def test_parity_finds_notes_by_slug(repo: Path):
    cfg = Config.load(repo)
    hit = parity._find_notes(repo, cfg, "v0.1.1")
    assert hit is not None and hit.name == "RELEASE-NOTES-v0.1.1.md"


def test_parity_full_local_contract(repo: Path):
    # The remote checks (origin push, gh release) fail in the synthetic repo;
    # assert the LOCAL checks: version parity + notes (notes exist for v0.1.1;
    # v0.1.0's notes are written here so the finding is only the remote pair).
    (repo / "docs" / "releases" / "myrepo" / "RELEASE-NOTES-v0.1.0.md").write_text(
        "# myrepo v0.1.0\n\nInitial release with the full notes body, well over the length check.\n"
    )
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-q", "-m", "docs: init release notes"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "tag", "-f", "v0.1.0"], cwd=repo, check=True, capture_output=True)
    cfg = Config.load(repo)
    result = parity.check(repo, cfg)
    text = "\n".join(result.findings)
    assert "version on disk" not in text
    assert "no source notes" not in text
    assert any("NO GitHub release" in f or "not pushed" in f for f in result.findings)
    assert result.ok is False


def test_parity_version_mismatch_reported(repo: Path):
    cfg = Config.load(repo)
    (repo / ".repolice.toml").write_text('owner = "s"\nrepo = "myrepo"\nversion_files = ["pyproject.toml"]\n')
    (repo / "pyproject.toml").write_text('[project]\nname = "myrepo"\nversion = "0.1.9"\n')
    cfg = Config.load(repo)
    result = parity.check(repo, cfg)
    assert any("version on disk (0.1.9) != tag (v0.1.0)" in f for f in result.findings)


def test_parity_flags_non_v_prefixed_latest(repo: Path):
    # a NEWER non-v tag becomes latest: the guard flags the v-prefix contract
    (repo / "later.py").write_text("y\n")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-q", "-m", "feat: later"], cwd=repo, check=True, capture_output=True)
    import time

    time.sleep(1.1)
    subprocess.run(["git", "tag", "0.2.0"], cwd=repo, check=True, capture_output=True)
    cfg = Config.load(repo)
    assert latest_tag(repo) == "0.2.0"  # newest by creatordate
    result = parity.check(repo, cfg)
    assert any("not v-prefixed" in f for f in result.findings)
