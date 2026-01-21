"""
Package registry and installed package helpers.
"""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path

from atopile.server.core import packages as core_packages
from atopile.server.models import registry as registry_model
from atopile.server.state import server_state

log = logging.getLogger(__name__)

# Track active package operations
_active_package_ops: dict[str, dict[str, object]] = {}
_package_op_counter = 0
_package_op_lock = threading.Lock()


def _version_is_newer(installed: str | None, latest: str | None) -> bool:
    """
    Check if latest version is newer than installed version.

    Simple semver comparison - handles common version formats.
    Returns False if either version is None or comparison fails.
    """
    return registry_model.version_is_newer(installed, latest)


def search_registry_packages(query: str):
    """Search the package registry for packages matching the query."""
    return registry_model.search_registry_packages(query)


def get_all_registry_packages():
    """
    Get all packages from the registry by querying multiple search terms.

    The registry API requires a search term (empty/wildcard returns 0 results).
    This function queries multiple terms and merges results to get all packages.
    """
    return registry_model.get_all_registry_packages()


def get_package_details_from_registry(identifier: str):
    """
    Get detailed package information from the registry.

    Fetches:
    - Full package info with stats (downloads)
    - List of releases (versions)
    """
    return registry_model.get_package_details_from_registry(identifier)


def get_installed_packages_for_project(project_root: Path):
    """
    Read installed packages from a project's ato.yaml dependencies section.
    """
    return core_packages.get_installed_packages_for_project(project_root)


def get_all_installed_packages(paths: list[Path]):
    """
    Get all installed packages across all projects in the given paths.

    Returns a dict of package_identifier -> PackageInfo, with installed_in
    tracking which projects have each package.
    """
    return core_packages.get_all_installed_packages(paths)


def enrich_packages_with_registry(packages: dict):
    """
    Enrich installed packages with metadata from the registry.

    Fetches latest_version, summary, homepage, etc. from the registry
    for each installed package.
    """
    return registry_model.enrich_packages_with_registry(packages)


async def refresh_packages_async() -> None:
    """Refresh packages and update server_state. Called after install/remove."""
    from atopile.server.state import PackageInfo as StatePackageInfo

    scan_paths = server_state._workspace_paths
    if not scan_paths:
        return

    try:
        packages_map: dict[str, StatePackageInfo] = {}
        registry_error: str | None = None

        # 1. Get installed packages
        installed = get_all_installed_packages(scan_paths)
        for pkg in installed.values():
            packages_map[pkg.identifier] = StatePackageInfo(
                identifier=pkg.identifier,
                name=pkg.name,
                publisher=pkg.publisher,
                version=pkg.version,
                installed=True,
                installed_in=pkg.installed_in,
            )

        # 2. Get ALL registry packages (uses multiple search terms)
        try:
            registry_packages = get_all_registry_packages()
            log.info(
                f"[refresh_packages_async] Registry returned {len(registry_packages)} packages"
            )

            # Merge registry data into packages_map
            for reg_pkg in registry_packages:
                if reg_pkg.identifier in packages_map:
                    # Update installed package with registry metadata
                    existing = packages_map[reg_pkg.identifier]
                    packages_map[reg_pkg.identifier] = StatePackageInfo(
                        identifier=existing.identifier,
                        name=existing.name,
                        publisher=existing.publisher,
                        version=existing.version,
                        latest_version=reg_pkg.latest_version,
                        description=reg_pkg.description or reg_pkg.summary,
                        summary=reg_pkg.summary,
                        homepage=reg_pkg.homepage,
                        repository=reg_pkg.repository,
                        license=reg_pkg.license,
                        installed=True,
                        installed_in=existing.installed_in,
                        has_update=_version_is_newer(
                            existing.version, reg_pkg.latest_version
                        ),
                        downloads=reg_pkg.downloads,
                        version_count=reg_pkg.version_count,
                        keywords=reg_pkg.keywords or [],
                    )
                else:
                    # Add uninstalled registry package
                    packages_map[reg_pkg.identifier] = StatePackageInfo(
                        identifier=reg_pkg.identifier,
                        name=reg_pkg.name,
                        publisher=reg_pkg.publisher,
                        latest_version=reg_pkg.latest_version,
                        description=reg_pkg.description or reg_pkg.summary,
                        summary=reg_pkg.summary,
                        homepage=reg_pkg.homepage,
                        repository=reg_pkg.repository,
                        license=reg_pkg.license,
                        installed=False,
                        installed_in=[],
                        has_update=False,
                        downloads=reg_pkg.downloads,
                        version_count=reg_pkg.version_count,
                        keywords=reg_pkg.keywords or [],
                    )

        except Exception as exc:
            registry_error = str(exc)
            log.warning(f"[refresh_packages_async] Registry fetch failed: {exc}")

        # Sort: installed first, then alphabetically
        state_packages = sorted(
            packages_map.values(),
            key=lambda p: (not p.installed, p.identifier.lower()),
        )

        await server_state.set_packages(list(state_packages), registry_error)
        log.info(
            f"Refreshed packages after install/remove: {len(state_packages)} packages"
        )
    except Exception as exc:
        log.error(f"Failed to refresh packages: {exc}")


def next_package_op_id(prefix: str) -> str:
    """Reserve and return a new package operation id."""
    global _package_op_counter
    with _package_op_lock:
        _package_op_counter += 1
        op_id = f"{prefix}-{_package_op_counter}-{int(time.time())}"
    return op_id


__all__ = [
    "_active_package_ops",
    "_package_op_counter",
    "_package_op_lock",
    "_version_is_newer",
    "enrich_packages_with_registry",
    "get_all_installed_packages",
    "get_all_registry_packages",
    "get_installed_packages_for_project",
    "get_package_details_from_registry",
    "next_package_op_id",
    "refresh_packages_async",
    "search_registry_packages",
]
