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
            log.info(f"Fetching versions from PyPI: {PYPI_URL}")
            response = await client.get(PYPI_URL)
            response.raise_for_status()
            data = response.json()

            releases = data.get("releases", {})
            log.info(f"Found {len(releases)} total releases on PyPI")

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

            log.info(
                f"Filtered to {len(versions)} compatible versions "
                f"(minimum: {'.'.join(map(str, MINIMUM_SUPPORTED_VERSION))})"
            )

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
        all_branches = []
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Paginate through all branches (max 100 per page)
            page = 1
            while True:
                response = await client.get(
                    GITHUB_API_BRANCHES,
                    params={"per_page": 100, "page": page},
                    headers={"Accept": "application/vnd.github.v3+json"},
                )
                response.raise_for_status()
                branches = response.json()

                if not branches:
                    break

                all_branches.extend([b["name"] for b in branches])

                # Stop if we got less than 100 (last page)
                if len(branches) < 100:
                    break
                page += 1

                # Safety limit to avoid infinite loops
                if page > 10:
                    break

            # Sort with main/develop/stage branches first
            def branch_priority(name: str) -> tuple:
                if name == "main":
                    return (0, name)
                if name == "develop":
                    return (1, name)
                if name == "master":
                    return (2, name)
                if name.startswith("stage/"):
                    return (3, name)
                if name.startswith("feature/"):
                    return (5, name)
                if name.startswith("fix/"):
                    return (6, name)
                return (4, name)

            all_branches.sort(key=branch_priority)
            log.info(f"Fetched {len(all_branches)} branches from GitHub")

            return all_branches
    except Exception as e:
        log.error(f"Failed to fetch GitHub branches: {e}")
        return ["main", "develop", "stage/0.14.x"]  # Fallback with common branches


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
            (".venv/bin/ato", None),  # local venv (dotted)
            ("venv/bin/ato", None),  # local venv (no dot)
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

    # Get the resolved binary path (first element of command, or second if using python)
    resolved_path = (
        command[-1] if len(command) > 1 and command[0] == sys.executable else command[0]
    )

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
            return {
                "valid": True,
                "version": version,
                "error": None,
                "resolved_path": resolved_path,
            }

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
            return {
                "valid": True,
                "version": version,
                "error": None,
                "resolved_path": resolved_path,
            }

        error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown error"
        return {
            "valid": False,
            "version": None,
            "error": f"Command failed: {error_msg[:100]}",
            "resolved_path": None,
        }
    except subprocess.TimeoutExpired:
        return {
            "valid": False,
            "version": None,
            "error": "Command timed out",
            "resolved_path": None,
        }
    except Exception as e:
        return {
            "valid": False,
            "version": None,
            "error": str(e)[:100],
            "resolved_path": None,
        }


def detect_local_installations(
    workspace_paths: Optional[list[str]] = None,
) -> list[dict]:
    """
    Detect existing atopile installations on the system and in workspaces.
    Returns list of DetectedInstallation dicts.

    Args:
        workspace_paths: Optional list of workspace root paths to check for local
                        atopile installations (e.g., monorepo development).
    """
    installations = []

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

    # Check workspace venvs and detect atopile monorepo
    workspace_root = os.environ.get("WORKSPACE_ROOT", os.getcwd())
    workspace_roots = [workspace_root]
    if workspace_paths:
        workspace_roots.extend(workspace_paths)

    for ws_root in workspace_roots:
        ws_path = Path(ws_root)

        # Check for venv installations
        for venv_name in [".venv", "venv"]:
            venv_ato = ws_path / venv_name / "bin" / "ato"
            if venv_ato.exists():
                version = _get_version(str(venv_ato))
                installations.append(
                    {
                        "path": str(venv_ato),
                        "version": version,
                        "source": "venv",
                    }
                )

        # Check if this workspace IS the atopile monorepo
        # Look for characteristic files that indicate this is the atopile source
        monorepo_indicators = [
            ws_path / "src" / "atopile" / "cli" / "cli.py",
            ws_path / "src" / "atopile" / "__init__.py",
            ws_path / "pyproject.toml",
        ]
        is_atopile_monorepo = all(
            indicator.exists() for indicator in monorepo_indicators
        )

        if is_atopile_monorepo:
            # Check if there's a pyproject.toml with atopile
            pyproject = ws_path / "pyproject.toml"
            if pyproject.exists():
                try:
                    content = pyproject.read_text()
                    if 'name = "atopile"' in content or "name = 'atopile'" in content:
                        # This is the atopile monorepo - add it as a workspace detection
                        # The path we return is the venv's ato binary if it exists,
                        # otherwise the source directory
                        venv_ato = ws_path / ".venv" / "bin" / "ato"
                        if venv_ato.exists():
                            version = _get_version(str(venv_ato))
                            installations.append(
                                {
                                    "path": str(venv_ato),
                                    "version": version,
                                    "source": "workspace",
                                }
                            )
                        else:
                            # Return workspace root - validation finds the binary
                            installations.append(
                                {
                                    "path": str(ws_path),
                                    "version": None,
                                    "source": "workspace",
                                }
                            )
                except Exception:
                    pass

    # Deduplicate by path (keep first occurrence)
    seen_paths = set()
    unique_installations = []
    for inst in installations:
        # Normalize path for deduplication
        norm_path = str(Path(inst["path"]).resolve())
        if norm_path not in seen_paths:
            seen_paths.add(norm_path)
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
