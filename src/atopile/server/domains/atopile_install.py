"""
Atopile installation management domain.

Handles fetching available versions, branches, validating local paths,
and detecting existing installations.
"""

import asyncio
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Optional

import httpx

log = logging.getLogger(__name__)

PYPI_URL = "https://pypi.org/pypi/atopile/json"
GITHUB_API_BRANCHES = "https://api.github.com/repos/atopile/atopile/branches"

# Minimum supported version for this extension
# Versions older than this won't be shown in the release dropdown
# Note: This only applies to releases - branches and local paths allow any version
MINIMUM_SUPPORTED_VERSION = (0, 14, 0)


def _parse_version(version_str: str) -> tuple[int, ...]:
    """Parse a version string into a tuple of integers for comparison."""
    parts = re.findall(r"\d+", version_str)
    return tuple(int(x) for x in parts) if parts else (0,)


def _version_meets_minimum(version_str: str) -> bool:
    """Check if a version string meets the minimum supported version."""
    version_tuple = _parse_version(version_str)
    # Pad with zeros if needed for comparison
    padded_version = version_tuple + (0,) * (3 - len(version_tuple))
    padded_minimum = MINIMUM_SUPPORTED_VERSION + (0,) * (
        3 - len(MINIMUM_SUPPORTED_VERSION)
    )
    return padded_version[:3] >= padded_minimum[:3]


async def fetch_available_versions() -> list[str]:
    """
    Fetch available atopile versions from PyPI.
    Returns a list of version strings, sorted newest first.
    Only includes versions >= MINIMUM_SUPPORTED_VERSION.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(PYPI_URL)
            response.raise_for_status()
            data = response.json()

            releases = data.get("releases", {})
            # Filter out pre-release versions and versions below minimum
            versions = []
            for version in releases.keys():
                # Skip dev, alpha, beta, rc versions
                if re.search(r"(dev|alpha|beta|rc|a\d|b\d)", version, re.IGNORECASE):
                    continue
                # Skip versions below minimum supported
                if not _version_meets_minimum(version):
                    continue
                versions.append(version)

            # Sort versions (newest first)
            versions.sort(key=_parse_version, reverse=True)

            # Limit to most recent versions (UI shows top 20)
            return versions[:25]
    except Exception as e:
        log.error(f"Failed to fetch PyPI versions: {e}")
        return []


async def fetch_available_branches() -> list[str]:
    """
    Fetch available branches from GitHub.
    Returns a list of branch names.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Get branches (UI filters and shows top 15)
            response = await client.get(
                GITHUB_API_BRANCHES,
                params={"per_page": 50},
                headers={"Accept": "application/vnd.github.v3+json"},
            )
            response.raise_for_status()
            branches = response.json()

            # Extract branch names
            branch_names = [b["name"] for b in branches]

            # Sort with main/develop first
            priority = {"main": 0, "develop": 1, "master": 2}
            branch_names.sort(key=lambda b: (priority.get(b, 100), b))

            return branch_names
    except Exception as e:
        log.error(f"Failed to fetch GitHub branches: {e}")
        return ["main", "develop"]  # Fallback


async def validate_local_path(path: str) -> dict:
    """
    Validate a local atopile path.
    Returns dict with:
        - valid: bool
        - version: Optional[str]
        - error: Optional[str]
    """
    import sys

    if not path:
        return {"valid": False, "version": None, "error": "No path provided"}

    path_obj = Path(path)

    # Check if path exists
    if not path_obj.exists():
        return {"valid": False, "version": None, "error": "Path does not exist"}

    # Determine command to run based on path type
    command: list[str] = []

    if path_obj.is_file():
        if path_obj.suffix == ".py":
            # Python script - run with python
            command = [sys.executable, str(path_obj)]
        else:
            # Assume it's an executable
            command = [str(path_obj)]
    elif path_obj.is_dir():
        # Look for ato binary in common locations
        candidates = [
            ("bin/ato", None),  # venv binary
            (".venv/bin/ato", None),  # local venv
            ("ato", None),  # direct binary
            ("src/atopile/cli/cli.py", sys.executable),  # source tree
        ]
        for candidate, python in candidates:
            candidate_path = path_obj / candidate
            if candidate_path.exists():
                if python:
                    command = [python, str(candidate_path)]
                else:
                    command = [str(candidate_path)]
                break

        if not command:
            return {
                "valid": False,
                "version": None,
                "error": "No ato binary found in directory",
            }
    else:
        return {"valid": False, "version": None, "error": "Invalid path type"}  # noqa: E501

    # Try to get version using self-check (fastest)
    try:
        result = await asyncio.to_thread(
            subprocess.run,
            command + ["self-check"],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=str(path_obj.parent) if path_obj.is_file() else str(path_obj),
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            return {"valid": True, "version": version, "error": None}

        # If self-check fails, try --version
        result = await asyncio.to_thread(
            subprocess.run,
            command + ["--version"],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=str(path_obj.parent) if path_obj.is_file() else str(path_obj),
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            return {"valid": True, "version": version, "error": None}

        error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown error"
        return {
            "valid": False,
            "version": None,
            "error": f"Command failed: {error_msg[:100]}",
        }
    except subprocess.TimeoutExpired:
        return {"valid": False, "version": None, "error": "Command timed out"}
    except Exception as e:
        return {"valid": False, "version": None, "error": str(e)[:100]}


def detect_local_installations() -> list[dict]:
    """
    Detect existing atopile installations on the system.
    Returns list of DetectedInstallation dicts.
    """
    installations = []

    # Check common locations
    locations_to_check = [  # noqa
        # User's PATH
        ("which", "path"),
        # Common venv locations
        (".venv/bin/ato", "venv"),
        ("venv/bin/ato", "venv"),
        # Common dev locations
        ("~/projects/atopile/src/atopile", "path"),
        ("~/dev/atopile/src/atopile", "path"),
    ]

    # Check PATH first
    try:
        result = subprocess.run(
            ["which", "ato"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            ato_path = result.stdout.strip()
            version = _get_version(ato_path)
            installations.append(
                {
                    "path": ato_path,
                    "version": version,
                    "source": "path",
                }
            )
    except Exception:
        pass

    # Check workspace venvs
    workspace_root = os.environ.get("WORKSPACE_ROOT", os.getcwd())
    for venv_name in [".venv", "venv"]:
        venv_ato = Path(workspace_root) / venv_name / "bin" / "ato"
        if venv_ato.exists():
            version = _get_version(str(venv_ato))
            installations.append(
                {
                    "path": str(venv_ato),
                    "version": version,
                    "source": "venv",
                }
            )

    # Deduplicate by path
    seen_paths = set()
    unique_installations = []
    for inst in installations:
        if inst["path"] not in seen_paths:
            seen_paths.add(inst["path"])
            unique_installations.append(inst)

    return unique_installations


def _get_version(binary_path: str) -> Optional[str]:
    """Get version from an ato binary."""
    try:
        result = subprocess.run(
            [binary_path, "self-check"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None
