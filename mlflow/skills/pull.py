from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from mlflow.entities.skill import SkillVersion
from mlflow.exceptions import MlflowException
from mlflow.protos.databricks_pb2 import INVALID_PARAMETER_VALUE

_GITHUB_TREE_RE = re.compile(
    r"^(?P<base>https?://github\.com/[^/]+/[^/]+)/tree/(?P<ref>[^/]+)(?:/(?P<path>.+))?$"
)


def pull_skill(
    skill_version: SkillVersion,
    destination: str | Path = ".",
) -> Path:
    if not skill_version.source:
        raise MlflowException(
            f"Skill version '{skill_version.name}' v{skill_version.version} "
            "has no source — nothing to pull.",
            error_code=INVALID_PARAMETER_VALUE,
        )

    source_type = skill_version.source_type or "git"
    if source_type != "git":
        raise MlflowException(
            f"Pull is not yet supported for source_type='{source_type}'. "
            "Only 'git' is supported in this release.",
            error_code=INVALID_PARAMETER_VALUE,
        )

    repo_url, ref, tree_path = _parse_git_source(skill_version.source)
    subpath = skill_version.subpath or tree_path

    dest = Path(destination)
    dest.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        clone_dir = Path(tmp) / "repo"
        _git_clone(repo_url, clone_dir, ref=ref, subpath=subpath)

        src = clone_dir / subpath if subpath else clone_dir
        if not src.exists():
            raise MlflowException(
                f"Subpath '{subpath}' does not exist in the cloned repository.",
                error_code=INVALID_PARAMETER_VALUE,
            )

        _copy_tree(src, dest)

    if skill_version.content_digest:
        _verify_digest(dest, skill_version.content_digest)

    return dest


def _parse_git_source(source: str) -> tuple[str, str | None, str | None]:
    m = _GITHUB_TREE_RE.match(source)
    if m:
        repo_url = m.group("base") + ".git"
        ref = m.group("ref")
        path = m.group("path")
        return repo_url, ref, path
    return source, None, None


def _git_clone(
    repo_url: str,
    dest: Path,
    ref: str | None = None,
    subpath: str | None = None,
) -> None:
    cmd = ["git", "clone", "--depth", "1"]
    if ref:
        cmd += ["--branch", ref]
    if subpath:
        cmd += ["--filter=blob:none", "--sparse"]

    cmd += [repo_url, str(dest)]
    subprocess.run(cmd, check=True, capture_output=True, text=True)

    if subpath:
        subprocess.run(
            ["git", "sparse-checkout", "set", subpath],
            cwd=dest,
            check=True,
            capture_output=True,
            text=True,
        )


def _copy_tree(src: Path, dest: Path) -> None:
    if src.is_dir():
        for item in src.iterdir():
            if item.name == ".git":
                continue
            target = dest / item.name
            if item.is_dir():
                shutil.copytree(item, target, dirs_exist_ok=True)
            else:
                shutil.copy2(item, target)
    else:
        shutil.copy2(src, dest / src.name)


def _verify_digest(directory: Path, expected: str) -> None:
    match expected.split(":", 1):
        case [algo, digest]:
            pass
        case _:
            algo, digest = "sha256", expected

    if algo != "sha256":
        raise MlflowException(
            f"Unsupported digest algorithm: '{algo}'. Only 'sha256' is supported.",
            error_code=INVALID_PARAMETER_VALUE,
        )

    actual = _compute_directory_digest(directory)
    if actual != digest:
        raise MlflowException(
            f"Content digest mismatch: expected {digest}, got {actual}",
            error_code=INVALID_PARAMETER_VALUE,
        )


def _compute_directory_digest(directory: Path) -> str:
    h = hashlib.sha256()
    for path in sorted(directory.rglob("*")):
        if path.is_file() and ".git" not in path.parts:
            rel = path.relative_to(directory)
            h.update(str(rel).encode())
            h.update(path.read_bytes())
    return h.hexdigest()
