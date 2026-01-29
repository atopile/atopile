"""
Atopile installation management domain.

Handles validating local atopile paths.
"""

import asyncio
import logging
import subprocess
import sys
from pathlib import Path

log = logging.getLogger(__name__)


async def validate_local_path(path: str) -> dict:
    """
    Validate a local atopile path.
    Returns dict with:
        - valid: bool
        - version: Optional[str]
        - error: Optional[str]
        - resolved_path: Optional[str] - the full path to the ato binary
    """
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
        return {"valid": False, "version": None, "error": "Invalid path type"}

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
