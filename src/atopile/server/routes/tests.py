"""
Test discovery and execution routes for the Test Explorer.

Endpoints:
- GET /api/tests/collect - Collect tests using pytest --collect-only
- GET /api/tests/last-run - Get most recent test run ID for a test name
- GET /api/tests/flags - Discover available ConfigFlags in the codebase
"""

import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

log = logging.getLogger(__name__)

router = APIRouter(tags=["tests"])


class TestItem(BaseModel):
    """A single test item discovered by pytest."""

    node_id: str  # Full pytest node ID: "test/foo.py::TestClass::test_method"
    file: str  # File path: "test/foo.py"
    class_name: Optional[str] = None  # Class name if test is in a class
    method_name: str  # Test function/method name
    display_name: str  # Human-readable display name


class CollectTestsResponse(BaseModel):
    """Response from test collection."""

    success: bool
    tests: list[TestItem]
    errors: dict[str, str]  # File path -> error message
    error: Optional[str] = None  # General error message


class LastRunResponse(BaseModel):
    """Response from last run lookup."""

    test_run_id: Optional[str] = None
    timestamp: Optional[str] = None
    found: bool = False


def _parse_node_id(node_id: str) -> TestItem:
    """Parse a pytest node ID into its components."""
    # Format: file.py::Class::method or file.py::function
    parts = node_id.split("::")

    file_path = parts[0] if parts else ""
    class_name: Optional[str] = None
    method_name = ""
    display_name = ""

    if len(parts) == 3:
        # file.py::Class::method
        class_name = parts[1]
        method_name = parts[2]
        display_name = f"{class_name}.{method_name}"
    elif len(parts) == 2:
        # file.py::function
        method_name = parts[1]
        display_name = method_name
    else:
        # Just file path
        method_name = node_id
        display_name = node_id

    return TestItem(
        node_id=node_id,
        file=file_path,
        class_name=class_name,
        method_name=method_name,
        display_name=display_name,
    )


def _collect_tests_sync(
    paths: str, filter_pattern: str, markers: str
) -> CollectTestsResponse:
    """
    Collect tests using pytest --collect-only.

    This is a sync function that should be run in a thread pool.
    """
    # Build pytest arguments
    pytest_args: list[str] = []

    # Add paths to search
    if paths.strip():
        pytest_args.extend(paths.strip().split())

    # Add filter pattern if provided (-k flag)
    if filter_pattern.strip():
        pytest_args.extend(["-k", filter_pattern.strip()])

    # Add markers if provided (-m flag)
    if markers.strip():
        pytest_args.extend(["-m", markers.strip()])

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "--collect-only",
        "-q",
        "--no-header",
        "--continue-on-collection-errors",
        # Ensure co-located tests are imported by package name
        "-p",
        "atopile.pytest_import_by_name",
    ] + pytest_args

    log.info(f"Collecting tests: {' '.join(cmd)}")

    try:
        env = os.environ.copy()
        env["PYTHONPATH"] = os.getcwd()

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            timeout=120,  # 2 minute timeout for collection
        )

        # Parse output
        split = result.stdout.split("\n\n", maxsplit=1)
        stdout = split[0] if split else ""
        summary = split[1] if len(split) == 2 else ""

        errors_clean: dict[str, str] = {}
        if result.returncode != 0:
            # Parse error messages
            if "ERRORS " not in summary and "ERRORS " in stdout:
                summary = stdout

            if "ERRORS " in summary:
                try:
                    error_parts = (
                        summary.split("ERRORS ")[1]
                        .strip()
                        .lstrip("=")
                        .split(" short test summary info")[0]
                        .rstrip("=")
                    )
                    for part in error_parts.split(" ERROR collecting ")[1:]:
                        pieces = part.strip().strip("_").strip().split("____\n")
                        if len(pieces) >= 2:
                            file_path = pieces[0].strip("_").strip()
                            error_msg = pieces[1]
                            errors_clean[file_path] = error_msg
                except Exception as parse_err:
                    log.warning(f"Failed to parse collection errors: {parse_err}")

        # Parse test node IDs
        tests: list[TestItem] = []
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("no tests ran"):
                continue
            if line.startswith("="):
                continue
            # Check if it looks like a node ID
            if "::" in line or line.endswith(".py"):
                tests.append(_parse_node_id(line))

        return CollectTestsResponse(
            success=True,
            tests=tests,
            errors=errors_clean,
        )

    except subprocess.TimeoutExpired:
        return CollectTestsResponse(
            success=False,
            tests=[],
            errors={},
            error="Test collection timed out after 120 seconds",
        )
    except Exception as exc:
        log.exception(f"Failed to collect tests: {exc}")
        return CollectTestsResponse(
            success=False,
            tests=[],
            errors={},
            error=str(exc),
        )


@router.get("/api/tests/collect", response_model=CollectTestsResponse)
async def collect_tests(
    paths: str = Query("test src", description="Space-separated paths to search"),
    filter: str = Query("", description="Filter pattern (-k flag)"),
    markers: str = Query("", description="Marker expression (-m flag)"),
) -> CollectTestsResponse:
    """
    Collect tests using pytest --collect-only.

    Returns a list of discovered test items with their node IDs parsed.
    """
    return await asyncio.to_thread(_collect_tests_sync, paths, filter, markers)


@router.get("/api/tests/last-run", response_model=LastRunResponse)
async def get_last_test_run(
    test_name: str = Query(..., description="Test name to look up"),
) -> LastRunResponse:
    """
    Get the most recent test_run_id for a given test name.

    This allows viewing the last run's logs when clicking a test in the explorer.
    """
    try:
        from atopile.logging import LoggerForTest

        db_path = LoggerForTest.get_log_db()
        if not db_path.exists():
            return LastRunResponse(found=False)

        import sqlite3

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Find the most recent test_run_id for this test name
        cursor.execute(
            """
            SELECT test_run_id, timestamp
            FROM test_logs
            WHERE test_name LIKE ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (f"%{test_name}%",),
        )

        row = cursor.fetchone()
        conn.close()

        if row:
            return LastRunResponse(
                found=True,
                test_run_id=row[0],
                timestamp=row[1],
            )

        return LastRunResponse(found=False)

    except Exception as exc:
        log.warning(f"Failed to get last test run: {exc}")
        return LastRunResponse(found=False)


class ConfigFlagItem(BaseModel):
    """A single ConfigFlag discovered in the codebase."""

    env_name: str  # Full env var name (e.g., "FBRK_SLOG")
    kind: str  # ConfigFlag type (e.g., "ConfigFlag", "ConfigFlagInt")
    python_name: Optional[str] = None  # Python variable name
    default: Optional[str] = None  # Default value as string
    current: Optional[str] = None  # Current value from env
    description: Optional[str] = None  # Description text


class FlagsResponse(BaseModel):
    """Response from flags discovery."""

    success: bool
    flags: list[ConfigFlagItem]
    error: Optional[str] = None


def _discover_flags_sync() -> FlagsResponse:
    """
    Discover ConfigFlags using AST-based analysis.

    This is a sync function that should be run in a thread pool.
    """
    try:
        from atopile.config_flags import discover_configflags, get_default_roots

        roots = get_default_roots()
        if not roots:
            return FlagsResponse(
                success=False,
                flags=[],
                error="Could not find src/atopile or src/faebryk directories",
            )

        discovered = discover_configflags(*roots)

        flags = [
            ConfigFlagItem(
                env_name=f.full_env_name,
                kind=f.kind,
                python_name=f.python_name,
                default=f.default,
                current=f.current_value,
                description=f.descr,
            )
            for f in discovered
        ]

        return FlagsResponse(success=True, flags=flags)

    except Exception as exc:
        log.exception(f"Failed to discover flags: {exc}")
        return FlagsResponse(success=False, flags=[], error=str(exc))


@router.get("/api/tests/flags", response_model=FlagsResponse)
async def get_flags() -> FlagsResponse:
    """
    Discover available ConfigFlags in the codebase.

    Returns a list of discovered ConfigFlags with their current values.
    """
    return await asyncio.to_thread(_discover_flags_sync)
