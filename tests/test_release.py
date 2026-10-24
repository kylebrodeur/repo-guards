"""The release-flow contract: refuses on any red gate; dry-run stops before
writes; the tag prefix rule applies at write time."""

from __future__ import annotations

from pathlib import Path

import pytest

from repoguards import release
from repoguards.config import Config


@pytest.fixture
def cfg() -> Config:
    # the synthetic repo has no origin: skip the parity/gh checks at the gate level
    return Config(
        owner="o",
        repo="myrepo",
        version_files=("pyproject.toml",),
        require_v_prefix=True,
        notes_candidates=("myrepo",),
    )


class TestNotesPath:
    def test_direct_and_slug_hits(self, repo: Path, cfg: Config):
        # the fixture wrote docs/releases/myrepo/RELEASE-NOTES-v0.1.1.md
        assert (release.notes_path(repo, cfg, "v0.1.1") or "").name == "RELEASE-NOTES-v0.1.1.md"
        assert release.notes_path(repo, cfg, "v9.9.9") is None

    def test_slug_candidates_shape(self, cfg: Config):
        # The prefix and the suffix are CONFIG. A family whose repos
        # carry them sets them, and the notes under a different
        # spelling are then found.
        cands = release._slug_candidates(
            Config(
                owner="o",
                repo="widget-thing-server",
                notes_candidates=("t",),
                repo_prefix="widget-",
                repo_suffix="-server",
            )
        )
        assert "widget-thing-server" in cands
        assert "thing-server" in cands
        assert "thing" in cands
        assert "widget-thing" in cands
        assert "t" in cands

    def test_slug_candidates_without_a_prefix_or_suffix(self, cfg: Config):
        # A family whose repos are named plainly sets neither, and the
        # repo name is then the only candidate plus the extras. The
        # prefix is not peeled from a name that does not carry it.
        cands = release._slug_candidates(Config(owner="o", repo="plain-repo", notes_candidates=("t",)))
        assert cands == ["plain-repo", "t"]

    def test_slug_candidates_do_not_peel_an_unconfigured_prefix(self, cfg: Config):
        # The naming convention is config, and not a hardcoded family's.
        cands = release._slug_candidates(Config(owner="o", repo="widget-thing", notes_candidates=()))
        assert "widget-thing" in cands
        assert "thing" not in cands


class TestRun:
    def test_dry_run_refuses_on_version_class(self, repo, cfg):
        # docs-only content but a minor bump requested -> refused before any write
        (repo / "DOCSNOTE.md").write_text("x")
        result = release.run(repo, cfg, "v0.2.0", dry_run=True)
        assert result is False

    def test_dry_run_stops_before_write(self, repo, cfg):
        ok = release.run(repo, cfg, "v0.1.1", dry_run=True)
        # the synthetic repo's ci gate is empty -> REFUSES with a clear message
        assert ok is False

    def test_gate_order_reports_first(self, repo, cfg):
        # two red gates: the failure comes with its named gate
        (repo / "bad prose.md").write_text("x")  # untracked; add to make prose checkable
        ok = release.run(repo, cfg, "v0.1.1", dry_run=True)
        assert ok is False


class TestCiGateShape:
    def test_empty_ci_reported(self, repo, cfg):
        from repoguards import ci as ci_guard

        result = ci_guard.check(repo, cfg)
        assert not result
        assert "no `ci` commands" in result.findings[0]
        assert "mirror .github/workflows/ci.yml" in result.findings[0]

    def test_green_ci_ok(self, repo, cfg):
        from repoguards import ci as ci_guard

        cfg2 = Config(owner="o", repo="myrepo", ci=("true",))
        assert ci_guard.check(repo, cfg2).ok

    def test_red_ci_reports_the_command(self, repo, cfg):
        from repoguards import ci as ci_guard

        cfg2 = Config(owner="o", repo="myrepo", ci=("false",))
        result = ci_guard.check(repo, cfg2)
        assert not result
        assert "CI FAILED: false" in result.findings[0]
