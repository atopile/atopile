"""
Package-related API routes.

Endpoints:
- GET /api/packages - List installed packages
- GET /api/packages/summary - Get packages with registry info merged
- GET /api/packages/{package_id} - Get package info
- GET /api/packages/{package_id}/details - Get detailed package info
- POST /api/packages/install - Install a package
- POST /api/packages/remove - Remove a package
- GET /api/registry/search - Search the package registry
"""

import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from ..schemas.package import (
    PackageInfo,
    PackageDetails,
    PackagesResponse,
    PackagesSummaryResponse,
    RegistrySearchResponse,
    PackageActionRequest,
    PackageActionResponse,
    RegistryStatus,
)

log = logging.getLogger(__name__)

router = APIRouter(tags=["packages"])


def _get_workspace_paths():
    """Get workspace paths from server state."""
    from ..server import state
    return state.get("workspace_paths", [])


@router.get("/api/packages", response_model=PackagesResponse)
async def list_packages(
    paths: Optional[str] = Query(None, description="Comma-separated list of paths to scan")
):
    """
    List installed packages across workspace projects.
    """
    from ..server import get_all_installed_packages

    if paths:
        scan_paths = [Path(p.strip()) for p in paths.split(",")]
    else:
        scan_paths = _get_workspace_paths()

    packages_map = get_all_installed_packages(scan_paths)
    packages = list(packages_map.values())

    return PackagesResponse(packages=packages, total=len(packages))


@router.get("/api/packages/summary", response_model=PackagesSummaryResponse)
async def get_packages_summary(
    paths: Optional[str] = Query(None, description="Comma-separated list of paths to scan")
):
    """
    Get packages with registry metadata merged.

    This is the main endpoint for the packages panel. It:
    1. Gets installed packages from workspace projects
    2. Fetches registry metadata
    3. Merges the data for display
    """
    from ..server import (
        get_all_installed_packages,
        get_all_registry_packages,
        _version_is_newer,
    )
    from ..schemas.package import PackageSummaryItem

    if paths:
        scan_paths = [Path(p.strip()) for p in paths.split(",")]
    else:
        scan_paths = _get_workspace_paths()

    # Get installed packages
    installed_map = get_all_installed_packages(scan_paths) if scan_paths else {}

    # Get registry packages
    registry_error = None
    registry_packages = []
    try:
        registry_packages = get_all_registry_packages()
    except Exception as e:
        registry_error = str(e)
        log.warning(f"Failed to fetch registry packages: {e}")

    # Merge into summary items
    packages_map: dict[str, PackageSummaryItem] = {}

    # Add installed packages first
    for pkg in installed_map.values():
        packages_map[pkg.identifier] = PackageSummaryItem(
            identifier=pkg.identifier,
            name=pkg.name,
            publisher=pkg.publisher,
            installed=True,
            version=pkg.version,
            installed_in=pkg.installed_in,
        )

    # Merge registry data
    for reg_pkg in registry_packages:
        if reg_pkg.identifier in packages_map:
            # Update existing with registry info
            existing = packages_map[reg_pkg.identifier]
            packages_map[reg_pkg.identifier] = PackageSummaryItem(
                identifier=existing.identifier,
                name=existing.name,
                publisher=existing.publisher,
                installed=True,
                version=existing.version,
                installed_in=existing.installed_in,
                latest_version=reg_pkg.latest_version,
                has_update=_version_is_newer(existing.version, reg_pkg.latest_version),
                summary=reg_pkg.summary,
                description=reg_pkg.description,
                homepage=reg_pkg.homepage,
                repository=reg_pkg.repository,
                license=reg_pkg.license,
                downloads=reg_pkg.downloads,
                version_count=reg_pkg.version_count,
                keywords=reg_pkg.keywords or [],
            )
        else:
            # Add uninstalled registry package
            packages_map[reg_pkg.identifier] = PackageSummaryItem(
                identifier=reg_pkg.identifier,
                name=reg_pkg.name,
                publisher=reg_pkg.publisher,
                installed=False,
                latest_version=reg_pkg.latest_version,
                summary=reg_pkg.summary,
                description=reg_pkg.description,
                homepage=reg_pkg.homepage,
                repository=reg_pkg.repository,
                license=reg_pkg.license,
                downloads=reg_pkg.downloads,
                version_count=reg_pkg.version_count,
                keywords=reg_pkg.keywords or [],
            )

    # Sort: installed first, then alphabetically
    packages = sorted(
        packages_map.values(),
        key=lambda p: (not p.installed, p.identifier.lower())
    )

    installed_count = sum(1 for p in packages if p.installed)

    return PackagesSummaryResponse(
        packages=packages,
        total=len(packages),
        installed_count=installed_count,
        registry_status=RegistryStatus(
            available=registry_error is None,
            error=registry_error
        )
    )


@router.get("/api/packages/{package_id:path}/details", response_model=PackageDetails)
async def get_package_details(
    package_id: str,
    paths: Optional[str] = Query(None, description="Comma-separated list of paths to check installation")
):
    """
    Get detailed information about a package from the registry.
    """
    from ..server import get_package_details_from_registry, get_all_installed_packages

    details = get_package_details_from_registry(package_id)
    if not details:
        raise HTTPException(status_code=404, detail=f"Package not found: {package_id}")

    # Check installation status
    if paths:
        scan_paths = [Path(p.strip()) for p in paths.split(",")]
        installed_map = get_all_installed_packages(scan_paths)
        if package_id in installed_map:
            details.installed = True
            details.installed_version = installed_map[package_id].version
            details.installed_in = installed_map[package_id].installed_in

    return details


@router.get("/api/packages/{package_id:path}", response_model=PackageInfo)
async def get_package_info(package_id: str):
    """
    Get basic information about a package.
    """
    from ..server import search_registry_packages

    # Search for the specific package
    results = search_registry_packages(package_id)
    for pkg in results:
        if pkg.identifier == package_id:
            return pkg

    raise HTTPException(status_code=404, detail=f"Package not found: {package_id}")


@router.get("/api/registry/search", response_model=RegistrySearchResponse)
async def search_registry(
    q: str = Query(..., description="Search query")
):
    """
    Search for packages in the registry.
    """
    from ..server import search_registry_packages

    packages = search_registry_packages(q)
    return RegistrySearchResponse(
        packages=packages,
        total=len(packages),
        query=q
    )


@router.post("/api/packages/install", response_model=PackageActionResponse)
async def install_package(request: PackageActionRequest):
    """
    Install a package into a project.
    """
    from ..server import install_package_to_project

    try:
        install_package_to_project(
            package_identifier=request.package_identifier,
            project_root=Path(request.project_root),
            version=request.version
        )
        return PackageActionResponse(
            success=True,
            message=f"Installed {request.package_identifier}",
            action="install"
        )
    except Exception as e:
        log.error(f"Failed to install package: {e}")
        return PackageActionResponse(
            success=False,
            message=str(e),
            action="install"
        )


@router.post("/api/packages/remove", response_model=PackageActionResponse)
async def remove_package(request: PackageActionRequest):
    """
    Remove a package from a project.
    """
    from ..server import remove_package_from_project

    try:
        remove_package_from_project(
            package_identifier=request.package_identifier,
            project_root=Path(request.project_root)
        )
        return PackageActionResponse(
            success=True,
            message=f"Removed {request.package_identifier}",
            action="remove"
        )
    except Exception as e:
        log.error(f"Failed to remove package: {e}")
        return PackageActionResponse(
            success=False,
            message=str(e),
            action="remove"
        )
