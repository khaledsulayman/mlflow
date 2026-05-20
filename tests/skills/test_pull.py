from __future__ import annotations

from pathlib import Path
from unittest import mock

import pytest

from mlflow.entities.skill import SkillVersion
from mlflow.exceptions import MlflowException
from mlflow.skills.pull import (
    _compute_directory_digest,
    _parse_git_source,
    pull_skill,
)


class TestParseGitSource:
    def test_github_tree_url(self):
        url = "https://github.com/acme/skills/tree/v1.0.0/code-review"
        repo, ref, path = _parse_git_source(url)
        assert repo == "https://github.com/acme/skills.git"
        assert ref == "v1.0.0"
        assert path == "code-review"

    def test_github_tree_url_nested_path(self):
        url = "https://github.com/acme/skills/tree/main/agents/code-review"
        repo, ref, path = _parse_git_source(url)
        assert repo == "https://github.com/acme/skills.git"
        assert ref == "main"
        assert path == "agents/code-review"

    def test_github_tree_url_no_path(self):
        url = "https://github.com/acme/skills/tree/v2.0.0"
        repo, ref, path = _parse_git_source(url)
        assert repo == "https://github.com/acme/skills.git"
        assert ref == "v2.0.0"
        assert path is None

    def test_plain_git_url(self):
        url = "https://github.com/acme/skills.git"
        repo, ref, path = _parse_git_source(url)
        assert repo == url
        assert ref is None
        assert path is None

    def test_ssh_url(self):
        url = "git@github.com:acme/skills.git"
        repo, ref, path = _parse_git_source(url)
        assert repo == url
        assert ref is None
        assert path is None


class TestPullSkill:
    def _make_version(self, **overrides) -> SkillVersion:
        defaults = {
            "name": "test-skill",
            "version": "1.0.0",
            "source_type": "git",
            "source": "https://github.com/acme/skills.git",
        }
        defaults.update(overrides)
        return SkillVersion(**defaults)

    def test_no_source_raises(self):
        sv = self._make_version(source=None)
        with pytest.raises(MlflowException, match="has no source"):
            pull_skill(sv)

    def test_unsupported_source_type_raises(self):
        sv = self._make_version(source_type="oci")
        with pytest.raises(MlflowException, match="not yet supported"):
            pull_skill(sv)

    @mock.patch("mlflow.skills.pull._git_clone")
    def test_pull_copies_files(self, mock_clone, tmp_path):
        def fake_clone(repo_url, dest, ref=None, subpath=None):
            dest.mkdir(parents=True, exist_ok=True)
            (dest / "SKILL.md").write_text("# Test Skill")
            (dest / "main.py").write_text("print('hello')")

        mock_clone.side_effect = fake_clone

        sv = self._make_version()
        dest = tmp_path / "output"
        result = pull_skill(sv, destination=dest)

        assert result == dest
        assert (dest / "SKILL.md").read_text() == "# Test Skill"
        assert (dest / "main.py").read_text() == "print('hello')"
        mock_clone.assert_called_once()

    @mock.patch("mlflow.skills.pull._git_clone")
    def test_pull_with_subpath(self, mock_clone, tmp_path):
        def fake_clone(repo_url, dest, ref=None, subpath=None):
            dest.mkdir(parents=True, exist_ok=True)
            sub = dest / "agents" / "reviewer"
            sub.mkdir(parents=True)
            (sub / "SKILL.md").write_text("# Reviewer")

        mock_clone.side_effect = fake_clone

        sv = self._make_version(subpath="agents/reviewer")
        dest = tmp_path / "output"
        result = pull_skill(sv, destination=dest)

        assert (dest / "SKILL.md").read_text() == "# Reviewer"

    @mock.patch("mlflow.skills.pull._git_clone")
    def test_pull_with_github_tree_url(self, mock_clone, tmp_path):
        def fake_clone(repo_url, dest, ref=None, subpath=None):
            dest.mkdir(parents=True, exist_ok=True)
            sub = dest / "code-review" if subpath else dest
            sub.mkdir(parents=True, exist_ok=True)
            (sub / "SKILL.md").write_text("# Code Review")

        mock_clone.side_effect = fake_clone

        sv = self._make_version(
            source="https://github.com/acme/skills/tree/v1.0.0/code-review"
        )
        dest = tmp_path / "output"
        pull_skill(sv, destination=dest)

        assert (dest / "SKILL.md").read_text() == "# Code Review"
        call_args = mock_clone.call_args
        assert call_args.kwargs.get("ref") == "v1.0.0" or call_args[0][0] == "https://github.com/acme/skills.git"

    @mock.patch("mlflow.skills.pull._git_clone")
    def test_pull_subpath_not_found(self, mock_clone, tmp_path):
        def fake_clone(repo_url, dest, ref=None, subpath=None):
            dest.mkdir(parents=True, exist_ok=True)

        mock_clone.side_effect = fake_clone

        sv = self._make_version(subpath="nonexistent/path")
        with pytest.raises(MlflowException, match="does not exist"):
            pull_skill(sv, destination=tmp_path / "output")

    @mock.patch("mlflow.skills.pull._git_clone")
    def test_pull_digest_match(self, mock_clone, tmp_path):
        def fake_clone(repo_url, dest, ref=None, subpath=None):
            dest.mkdir(parents=True, exist_ok=True)
            (dest / "hello.txt").write_text("hello")

        mock_clone.side_effect = fake_clone

        dest = tmp_path / "output"
        dest.mkdir()
        (dest / "hello.txt").write_text("hello")
        expected_digest = _compute_directory_digest(dest)

        dest2 = tmp_path / "output2"
        sv = self._make_version(content_digest=f"sha256:{expected_digest}")
        pull_skill(sv, destination=dest2)

    @mock.patch("mlflow.skills.pull._git_clone")
    def test_pull_digest_mismatch(self, mock_clone, tmp_path):
        def fake_clone(repo_url, dest, ref=None, subpath=None):
            dest.mkdir(parents=True, exist_ok=True)
            (dest / "hello.txt").write_text("hello")

        mock_clone.side_effect = fake_clone

        sv = self._make_version(content_digest="sha256:badhash")
        with pytest.raises(MlflowException, match="Content digest mismatch"):
            pull_skill(sv, destination=tmp_path / "output")

    @mock.patch("mlflow.skills.pull._git_clone")
    def test_pull_default_source_type_is_git(self, mock_clone, tmp_path):
        def fake_clone(repo_url, dest, ref=None, subpath=None):
            dest.mkdir(parents=True, exist_ok=True)
            (dest / "SKILL.md").write_text("# Skill")

        mock_clone.side_effect = fake_clone

        sv = self._make_version(source_type=None)
        dest = tmp_path / "output"
        pull_skill(sv, destination=dest)
        assert (dest / "SKILL.md").exists()


class TestComputeDirectoryDigest:
    def test_deterministic(self, tmp_path):
        (tmp_path / "a.txt").write_text("aaa")
        (tmp_path / "b.txt").write_text("bbb")
        d1 = _compute_directory_digest(tmp_path)
        d2 = _compute_directory_digest(tmp_path)
        assert d1 == d2

    def test_different_content(self, tmp_path):
        d1_path = tmp_path / "d1"
        d2_path = tmp_path / "d2"
        d1_path.mkdir()
        d2_path.mkdir()
        (d1_path / "a.txt").write_text("aaa")
        (d2_path / "a.txt").write_text("bbb")
        assert _compute_directory_digest(d1_path) != _compute_directory_digest(d2_path)

    def test_ignores_git_dir(self, tmp_path):
        (tmp_path / "a.txt").write_text("aaa")
        d1 = _compute_directory_digest(tmp_path)
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "HEAD").write_text("ref: refs/heads/main")
        d2 = _compute_directory_digest(tmp_path)
        assert d1 == d2
