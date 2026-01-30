# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
Package metadata for tracking installed package state and integrity.

This module provides functionality to:
- Track package installation metadata (version, source, timestamps)
- Compute and verify file checksums for integrity checking
- Detect local modifications to installed packages
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from hashlib import sha256
from pathlib import Path

from atopile import version as ato_version

logger = logging.getLogger(__name__)

PACKAGE_META_FILENAME = ".package_meta.json"
SCHEMA_VERSION = 1


class PackageState(Enum):
    """State of an installed package."""

    NOT_INSTALLED = "not_installed"
    """Package directory doesn't exist."""

    INSTALLED_FRESH = "installed_fresh"
    """Package is installed and matches manifest exactly."""

    INSTALLED_WRONG_VERSION = "wrong_version"
    """Different version is installed than what's in manifest."""

    INSTALLED_MODIFIED = "modified"
    """Package files have been locally modified."""

    INSTALLED_NO_META = "no_meta"
    """Untracked package - installed before metadata tracking was added."""


class PackageModifiedError(Exception):
    """Raised when a package has been locally modified."""

    def __init__(
        self,
        identifier: str,
        modified_files: list[str],
        package_path: Path | None = None,
    ):
        self.identifier = identifier
        self.modified_files = modified_files
        self.package_path = package_path
        files_str = ", ".join(modified_files[:5])
        if len(modified_files) > 5:
            files_str += f" and {len(modified_files) - 5} more"

        # Build the suggested destination path
        owner, name = identifier.split("/") if "/" in identifier else ("", identifier)
        suggested_dest = f"elec/{name}" if name else f"elec/{identifier}"

        super().__init__(
            f"Package '{identifier}' has local modifications in: {files_str}\n\n"
            f"To keep your changes, copy the package to your project:\n"
            f"  cp -r .ato/modules/{identifier} {suggested_dest}\n"
            f"Then update your imports to use the local copy.\n\n"
            f"Other options:\n"
            f"  - Run 'ato sync --force' to discard your changes\n"
            f"  - Run 'ato remove {identifier}' then 'ato add {identifier}'"
        )


@dataclass
class PackageSource:
    """Information about where a package was installed from."""

    type: str  # "registry", "git", "file"
    url: str | None = None  # Registry URL or git repo URL
    ref: str | None = None  # Git ref (branch/tag/commit)
    path: str | None = None  # Local path for file deps, path within repo for git

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "url": self.url,
            "ref": self.ref,
            "path": self.path,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PackageSource":
        return cls(
            type=data["type"],
            url=data.get("url"),
            ref=data.get("ref"),
            path=data.get("path"),
        )


@dataclass
class PackageMeta:
    """
    Metadata for an installed package.

    This is stored in .package_meta.json in the package directory and tracks:
    - Package identity and version
    - Installation source and timestamp
    - File checksums for integrity verification
    """

    schema_version: int
    identifier: str
    version: str
    source: PackageSource
    installed_at: str  # ISO format timestamp
    installed_by: str  # atopile version that installed it
    file_checksums: dict[str, str] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        identifier: str,
        version: str,
        source: PackageSource,
        package_path: Path,
    ) -> "PackageMeta":
        """Create metadata for a newly installed package."""
        file_checksums = cls._compute_checksums(package_path)

        # Convert Version object to string for JSON serialization
        installed_version = ato_version.clean_version(
            ato_version.get_installed_atopile_version()
        )

        return cls(
            schema_version=SCHEMA_VERSION,
            identifier=identifier,
            version=version,
            source=source,
            installed_at=datetime.now().isoformat(),
            installed_by=str(installed_version),
            file_checksums=file_checksums,
        )

    @staticmethod
    def _compute_checksums(package_path: Path) -> dict[str, str]:
        """Compute SHA256 checksums for all files in the package."""
        checksums = {}
        for file_path in package_path.rglob("*"):
            if not file_path.is_file():
                continue
            # Skip the metadata file itself
            if file_path.name == PACKAGE_META_FILENAME:
                continue
            # Skip hidden files/directories
            rel_path = file_path.relative_to(package_path)
            if any(part.startswith(".") for part in rel_path.parts):
                continue

            try:
                content = file_path.read_bytes()
                checksum = sha256(content).hexdigest()
                checksums[str(rel_path)] = checksum
            except (IOError, OSError) as e:
                logger.warning(f"Could not read file for checksum: {file_path}: {e}")

        return checksums

    def verify_integrity(self, package_path: Path) -> list[str]:
        """
        Verify that installed files match their checksums.

        Returns a list of modified file paths. Empty list means all files match.
        """
        modified_files = []

        for rel_path_str, expected_checksum in self.file_checksums.items():
            file_path = package_path / rel_path_str

            if not file_path.exists():
                modified_files.append(f"{rel_path_str} (deleted)")
                continue

            try:
                content = file_path.read_bytes()
                actual_checksum = sha256(content).hexdigest()
                if actual_checksum != expected_checksum:
                    modified_files.append(rel_path_str)
            except (IOError, OSError) as e:
                logger.warning(f"Could not verify file: {file_path}: {e}")
                modified_files.append(f"{rel_path_str} (unreadable)")

        # Check for new files that weren't in the original install
        current_checksums = self._compute_checksums(package_path)
        for rel_path_str in current_checksums:
            if rel_path_str not in self.file_checksums:
                modified_files.append(f"{rel_path_str} (added)")

        return modified_files

    def save(self, package_path: Path) -> None:
        """Save metadata to the package directory."""
        meta_path = package_path / PACKAGE_META_FILENAME
        data = {
            "schema_version": self.schema_version,
            "identifier": self.identifier,
            "version": self.version,
            "source": self.source.to_dict(),
            "installed_at": self.installed_at,
            "installed_by": self.installed_by,
            "file_checksums": self.file_checksums,
        }
        meta_path.write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls, package_path: Path) -> "PackageMeta | None":
        """Load metadata from a package directory. Returns None if not found."""
        meta_path = package_path / PACKAGE_META_FILENAME
        if not meta_path.exists():
            return None

        try:
            data = json.loads(meta_path.read_text())
            return cls(
                schema_version=data["schema_version"],
                identifier=data["identifier"],
                version=data["version"],
                source=PackageSource.from_dict(data["source"]),
                installed_at=data["installed_at"],
                installed_by=data["installed_by"],
                file_checksums=data.get("file_checksums", {}),
            )
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"Could not load package metadata from {meta_path}: {e}")
            return None

    @classmethod
    def exists(cls, package_path: Path) -> bool:
        """Check if metadata file exists in the package directory."""
        return (package_path / PACKAGE_META_FILENAME).exists()


def get_package_state(
    package_path: Path,
    expected_version: str | None = None,
    check_integrity: bool = True,
) -> tuple[PackageState, PackageMeta | None, list[str]]:
    """
    Determine the state of an installed package.

    Args:
        package_path: Path to the installed package directory
        expected_version: Expected version from manifest
            (for version mismatch detection)
        check_integrity: Whether to verify file checksums
            (can be slow for large packages)

    Returns:
        Tuple of (state, metadata, modified_files)
        - state: The PackageState enum value
        - metadata: PackageMeta if available, None otherwise
        - modified_files: List of modified file paths if state is INSTALLED_MODIFIED
    """
    if not package_path.exists():
        return PackageState.NOT_INSTALLED, None, []

    meta = PackageMeta.load(package_path)
    if meta is None:
        return PackageState.INSTALLED_NO_META, None, []

    # Check version mismatch
    if expected_version is not None and meta.version != expected_version:
        return PackageState.INSTALLED_WRONG_VERSION, meta, []

    # Check integrity
    if check_integrity:
        modified_files = meta.verify_integrity(package_path)
        if modified_files:
            return PackageState.INSTALLED_MODIFIED, meta, modified_files

    return PackageState.INSTALLED_FRESH, meta, []
