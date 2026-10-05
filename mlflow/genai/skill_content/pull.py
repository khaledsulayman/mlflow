"""
Client-side pull of a registered skill version to the local filesystem.

The registry is consulted only for version metadata; content is fetched directly from the
version's persisted source with the caller's own credentials, through the same fetchers that
registration and import use. Output is staged away from the requested destination, checked
for entry types and the recorded digest there, and published only once every check passes, so
a failed pull leaves the destination exactly as it was found.
"""

from __future__ import annotations

import errno
import os
import shutil
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path

from mlflow.entities.skill import SkillStatus
from mlflow.entities.skill_source import (
    GitSource,
    MlflowSource,
    OCISource,
    SkillSourceType,
    ZipSource,
)
from mlflow.entities.skill_version import SkillVersion
from mlflow.exceptions import MlflowException
from mlflow.genai.skill_content.digest import compute_tree_digest
from mlflow.genai.skill_content.errors import display_path, invalid_content, redact_credentials
from mlflow.genai.skill_content.fetchers import fetch_source
from mlflow.genai.skill_content.paths import _is_link_like
from mlflow.genai.skill_content.sources import is_local_path, resolve_source_type
from mlflow.protos.databricks_pb2 import INVALID_STATE, RESOURCE_DOES_NOT_EXIST
from mlflow.tracking.client import MlflowClient
from mlflow.utils.skill_uris import ParsedSkillUri, format_skill_uri, parse_skill_uri

_STAGING_PREFIX = ".mlflow-skill-pull-"


@dataclass(frozen=True)
class _Destination:
    path: Path
    # True when the destination is an existing empty directory, which publication fills in
    # place; otherwise it does not exist and publication creates it.
    exists: bool
    # Missing ancestors created for the pull, deepest first, removed again if it fails.
    created_parents: tuple[Path, ...] = ()


def resolve_skill_version(uri: str, client: MlflowClient | None = None) -> SkillVersion:
    """
    Resolve a ``skills:/`` URI to a version through registry metadata.

    ``skills:/name/3`` selects an exact version, ``skills:/name@alias`` follows an alias, and a
    bare ``skills:/name`` resolves the dynamic latest version at the time of the call.
    """
    parsed = parse_skill_uri(uri)
    client = client or MlflowClient()
    if parsed.version is not None:
        return client.get_skill_version(
            name=parsed.name, version=parsed.version, organization=parsed.organization
        )
    if parsed.alias is not None:
        return client.get_skill_version_by_alias(
            name=parsed.name, alias=parsed.alias, organization=parsed.organization
        )
    return client.get_latest_skill_version(name=parsed.name, organization=parsed.organization)


def default_destination(uri: str) -> Path:
    """The directory a pull writes to when none is given: the skill's name under the cwd."""
    return Path.cwd() / parse_skill_uri(uri).name


def pull_skill_version(version: SkillVersion, destination: str | os.PathLike[str]) -> Path:
    """
    Materialize ``version``'s content at ``destination`` and return the destination path.

    The content comes from the version's persisted source and, when set, only its persisted
    subpath; plugin membership is never consulted. ``destination`` must not exist or must be
    an empty directory; any other state is rejected before anything is fetched. A version with
    a recorded digest must match it; one without a digest is published unverified. On any
    failure the destination is left as it was found: still absent, or still empty.
    """
    uri = _version_uri(version)
    if version.status == SkillStatus.DELETED:
        raise MlflowException(
            f"Skill version '{uri}' has been deleted and cannot be pulled.",
            error_code=RESOURCE_DOES_NOT_EXIST,
        )
    source, subpath = _fetchable_source(version, uri)
    # abspath also folds ``..`` segments, so the parent and name used for staging and
    # publication are those of the directory the caller named.
    target = _check_destination(Path(os.path.abspath(Path(destination).expanduser())))
    target = _create_parents(target)
    try:
        staging = _make_staging_dir(target.path.parent)
        try:
            # fetch_source applies the subpath with containment checks and rejects symbolic
            # links, hard links, and special files in the selected tree for every source type.
            with fetch_source(source, subpath=subpath, destination=staging / "content") as fetched:
                root = fetched.root
            _verify_digest(root, version, uri)
            _publish(root, target)
        finally:
            shutil.rmtree(staging, ignore_errors=True)
    except BaseException:
        _remove_created_parents(target)
        raise
    return target.path


def _version_uri(version: SkillVersion) -> str:
    return format_skill_uri(
        ParsedSkillUri(
            name=version.name, organization=version.organization or "", version=version.version
        )
    )


def _fetchable_source(
    version: SkillVersion, uri: str
) -> tuple[GitSource | OCISource | ZipSource | str, str | None]:
    """
    The fetch_source arguments for ``version``'s persisted source.

    Typed Git, OCI, and ZIP sources carry their own ref and subpath. An MLflow source is its
    artifact tree plus the persisted subpath. Whatever the metadata says, it is only ever
    fetched as a remote or MLflow artifact location: a value that would resolve to a path on
    the caller's filesystem is refused, so registry metadata can never make a pull copy local
    files into the destination.
    """
    match version.source:
        case GitSource(url=url) if is_local_path(url.strip()):
            raise invalid_content(
                f"Skill version '{uri}' has a Git source that is a local path, not a remote "
                f"repository: '{url}'."
            )
        case GitSource() | OCISource() | ZipSource() as source:
            # Applies the same URL, ref, and credential checks as registration.
            resolve_source_type(source)
            return source, None
        case MlflowSource(artifact_path=artifact_path, subpath=subpath):
            resolved = resolve_source_type(artifact_path, subpath=subpath)
            if resolved.is_local or resolved.source_type != SkillSourceType.MLFLOW:
                raise invalid_content(
                    f"Skill version '{uri}' has an MLflow source that is not an MLflow artifact "
                    f"location: '{artifact_path}'."
                )
            return resolved.source, resolved.subpath
        case _:
            raise MlflowException.invalid_parameter_value(
                f"Skill version '{uri}' has no source that can be pulled "
                f"(source type: {version.source_type})."
            )


def _check_destination(path: Path) -> _Destination:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return _Destination(path=path, exists=False)
    except OSError as e:
        raise _destination_error(path, e.strerror or str(e)) from e
    if stat.S_ISLNK(info.st_mode) or _is_link_like(path):
        raise _destination_error(path, "it is a symbolic link")
    if not stat.S_ISDIR(info.st_mode):
        raise _destination_error(path, "it exists and is not a directory")
    try:
        is_empty = next(path.iterdir(), None) is None
    except OSError as e:
        raise _destination_error(path, e.strerror or str(e)) from e
    if not is_empty:
        raise _destination_error(path, "it is a directory that is not empty")
    return _Destination(path=path, exists=True)


def _destination_error(path: Path, reason: str) -> MlflowException:
    return MlflowException.invalid_parameter_value(
        f"Cannot pull into '{display_path(str(path))}': {reason}. The destination must not "
        "exist or must be an empty directory."
    )


def _create_parents(target: _Destination) -> _Destination:
    if target.exists:
        return target
    missing = []
    parent = target.path.parent
    while not os.path.lexists(parent):
        missing.append(parent)
        parent = parent.parent
    created = []
    try:
        for directory in reversed(missing):
            directory.mkdir()
            created.insert(0, directory)
    except OSError as e:
        _remove_dirs(created)
        raise _destination_error(target.path, e.strerror or str(e)) from e
    return _Destination(path=target.path, exists=False, created_parents=tuple(created))


def _remove_created_parents(target: _Destination) -> None:
    _remove_dirs(target.created_parents)


def _remove_dirs(directories) -> None:
    for directory in directories:
        try:
            directory.rmdir()
        except OSError:
            # Something else was put there while the pull ran; leave it.
            break


def _make_staging_dir(parent: Path) -> Path:
    # Staging beside the destination keeps publication a rename on the same filesystem. A
    # parent the caller cannot write to (an empty mount point, say) falls back to the system
    # temporary directory, and publication then copies across filesystems.
    try:
        return Path(tempfile.mkdtemp(prefix=_STAGING_PREFIX, dir=parent))
    except OSError:
        return Path(tempfile.mkdtemp(prefix=_STAGING_PREFIX))


def _verify_digest(root: Path, version: SkillVersion, uri: str) -> None:
    if version.digest is None:
        return
    actual = compute_tree_digest(root)
    if actual != version.digest:
        raise MlflowException(
            f"Content fetched for skill version '{uri}' does not match its recorded digest: "
            f"expected {version.digest}, got {actual}. The source has changed since the "
            "version was registered; nothing was written to the destination.",
            error_code=INVALID_STATE,
        )


def _publish(root: Path, target: _Destination) -> None:
    if target.exists:
        _publish_into_empty_directory(root, target.path)
    else:
        _publish_new_directory(root, target.path)


def _publish_new_directory(root: Path, destination: Path) -> None:
    try:
        # Atomic on one filesystem, and refuses to replace a file or a non-empty directory
        # that appeared at the destination while the content was fetched.
        root.rename(destination)
        return
    except OSError as e:
        if e.errno != errno.EXDEV:
            raise _publish_error(destination, e) from e
    try:
        shutil.copytree(root, destination)
    except FileExistsError as e:
        raise _publish_error(destination, e) from e
    except BaseException as e:
        shutil.rmtree(destination, ignore_errors=True)
        if isinstance(e, OSError):
            raise _publish_error(destination, e) from e
        raise


def _publish_into_empty_directory(root: Path, destination: Path) -> None:
    # The destination itself is kept (with its ownership and permissions), so its entries are
    # moved in one by one; if any move fails, those already moved are removed again so the
    # directory is left empty, as it was found.
    _check_destination(destination)
    moved = []
    try:
        for entry in sorted(root.iterdir()):
            target = destination / entry.name
            if os.path.lexists(target):
                raise FileExistsError(errno.EEXIST, "an entry appeared during the pull", target)
            # Recorded before the move: across filesystems a failed move can leave a partial
            # copy at the target, which must be removed as well.
            moved.append(target)
            shutil.move(entry, target)
    except BaseException as e:
        for target in moved:
            if target.is_dir() and not target.is_symlink():
                shutil.rmtree(target, ignore_errors=True)
            elif os.path.lexists(target):
                target.unlink()
        if isinstance(e, OSError):
            raise _publish_error(destination, e) from e
        raise


def _publish_error(destination: Path, error: OSError) -> MlflowException:
    return MlflowException(
        f"Failed to write pulled skill content to '{display_path(str(destination))}': "
        f"{redact_credentials(error.strerror or str(error))}"
    )
