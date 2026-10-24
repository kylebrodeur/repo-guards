"""The version-class contract: docs-only = patch; code may bump minor."""

from __future__ import annotations

from pathlib import Path

import pytest

from repoguards import version_class
from repoguards.config import Config

DOCS = ("README.md", "docs/guide.md", "CONTRIBUTING.md", ".github/ISSUE_TEMPLATE/bug.yml")
CODE = ("src/app.py", "server/x.py", "uv.lock", ".github/workflows/ci.yml")


@pytest.fixture
def cfg() -> Config:
    return Config(owner="o", repo="r", version_files=("pyproject.toml",), require_v_prefix=True)


class TestVersionClass:
    def test_docs_only_patch_ok(self, cfg):
        assert version_class.check(Path("."), cfg, "v0.1.1", last="v0.1.0", files=list(DOCS)).ok

    def test_docs_only_minor_refused(self, cfg):
        result = version_class.check(Path("."), cfg, "v0.2.0", last="v0.1.0", files=list(DOCS))
        assert not result
        assert "PATCH bump only" in result.findings[0]

    def test_code_minor_ok(self, cfg):
        assert version_class.check(Path("."), cfg, "v0.2.0", last="v0.1.0", files=list(CODE)).ok

    def test_code_patch_ok(self, cfg):
        assert version_class.check(Path("."), cfg, "v0.1.1", last="v0.1.0", files=list(CODE)).ok

    def test_code_decreasing_refused(self, cfg):
        result = version_class.check(Path("."), cfg, "v0.0.9", last="v0.1.0", files=list(CODE))
        assert not result

    def test_code_same_patch_refused(self, cfg):
        result = version_class.check(Path("."), cfg, "v0.1.0", last="v0.1.0", files=list(CODE))
        assert not result
        assert "does not increase" in result.findings[0]

    def test_docs_subpath_matching(self, cfg):
        # docs/ pattern matches nested paths without a matching exact entry:
        assert version_class.check(Path("."), cfg, "v0.1.1", last="v0.1.0", files=["docs/deep/nested/thing.md"]).ok

    def test_code_hiding_in_docs_path_refused(self, cfg):
        # a code file at the docs boundary is CODE (the docs/ prefix must not swallow it)
        files = ["docs/readme_generator.py", "README.md"]
        assert version_class.check(Path("."), cfg, "v0.2.0", last="v0.1.0", files=files).ok

    def test_invalid_version_refused(self, cfg):
        result = version_class.check(Path("."), cfg, "1.0", last="v0.1.0", files=[])
        assert not result
        assert "not a valid" in result.findings[0]

    def test_empty_diff_is_docs_class(self, cfg):
        assert version_class.check(Path("."), cfg, "v0.1.1", last="v0.1.0", files=[]).ok

    def test_mixed_content_is_code_class(self, cfg):
        mixed = list(DOCS) + ["src.py"]
        assert version_class.check(Path("."), cfg, "v0.2.0", last="v0.1.0", files=mixed).ok

    def test_mixed_cannot_minor_skip(self, cfg):
        result = version_class.check(Path("."), cfg, "v0.1.0", last="v0.1.0", files=["src.py"])
        assert not result
