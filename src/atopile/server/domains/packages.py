"""Package-related endpoints."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query

from atopile.server.app_context import AppContext
from atopile.server.domains.deps import get_ctx
from atopile.server import package_manager
from atopile.server.schemas.package import (
    PackageInfo,
    PackagesResponse,
    PackageDetails,
    PackageActionRequest,
    PackageActionResponse,
    RegistrySearchResponse,
    PackageSummaryItem,
    PackagesSummaryResponse,
    RegistryStatus,
)

log = logging.getLogger(__name__)

router = APIRouter(tags=["packages"])


@router.get("/api/registry/search", response_model=RegistrySearchResponse)
async def search_registry(
    query: str = Query("", description="Search query. Empty returns popular packages."),
    paths: Optional[str] = Query(
        None, description="Comma-separated list of paths to check installed packages."
    ),
    ctx: AppContext = Depends(get_ctx),
):
    registry_packages = package_manager.search_registry_packages(query)

    if paths:
        scan_paths = [Path(p.strip()) for p in paths.split(",")]
    else:
        scan_paths = ctx.workspace_paths

    if scan_paths:
        installed_map = package_manager.get_all_installed_packages(scan_paths)
        for pkg in registry_packages:
            if pkg.identifier in installed_map:
                installed = installed_map[pkg.identifier]
                pkg.installed = True
                pkg.installed_in = installed.installed_in
                pkg.version = installed.version

    return RegistrySearchResponse(
        packages=registry_packages,
        total=len(registry_packages),
        query=query,
    )


@router.get("/api/packages/summary", response_model=PackagesSummaryResponse)
async def get_packages_summary(
    paths: Optional[str] = Query(
        None,
        description="Comma-separated list of paths to scan for projects. If not provided, uses configured workspace paths.",
    ),
    ctx: AppContext = Depends(get_ctx),
):
    if paths:
        scan_paths = [Path(p.strip()) for p in paths.split(",")]
    else:
        scan_paths = ctx.workspace_paths

    packages_map: dict[str, PackageSummaryItem] = {}
    installed_count = 0

    if scan_paths:
        installed = package_manager.get_all_installed_packages(scan_paths)
        installed_count = len(installed)
        for identifier, pkg in installed.items():
            packages_map[identifier] = PackageSummaryItem(
                identifier=pkg.identifier,
                name=pkg.name,
                publisher=pkg.publisher,
                installed=True,
                version=pkg.version,
                installed_in=pkg.installed_in,
            )

    registry_status = RegistryStatus(available=True, error=None)
    registry_error: str | None = None

    try:
        registry_packages = package_manager.get_all_registry_packages()
        for reg_pkg in registry_packages:
            if reg_pkg.identifier in packages_map:
                existing = packages_map[reg_pkg.identifier]
                packages_map[reg_pkg.identifier] = PackageSummaryItem(
                    identifier=existing.identifier,
                    name=existing.name,
                    publisher=existing.publisher,
                    installed=True,
                    version=existing.version,
                    installed_in=existing.installed_in,
                    latest_version=reg_pkg.latest_version,
                    has_update=package_manager._version_is_newer(
                        existing.version, reg_pkg.latest_version
                    ),
                    summary=reg_pkg.summary,
                    description=reg_pkg.description or reg_pkg.summary,
                    homepage=reg_pkg.homepage,
                    repository=reg_pkg.repository,
                    license=reg_pkg.license,
                    downloads=reg_pkg.downloads,
                    version_count=reg_pkg.version_count,
                    keywords=reg_pkg.keywords or [],
                )
            else:
                packages_map[reg_pkg.identifier] = PackageSummaryItem(
                    identifier=reg_pkg.identifier,
                    name=reg_pkg.name,
                    publisher=reg_pkg.publisher,
                    installed=False,
                    latest_version=reg_pkg.latest_version,
                    has_update=False,
                    summary=reg_pkg.summary,
                    description=reg_pkg.description or reg_pkg.summary,
                    homepage=reg_pkg.homepage,
                    repository=reg_pkg.repository,
                    license=reg_pkg.license,
                    downloads=reg_pkg.downloads,
                    version_count=reg_pkg.version_count,
                    keywords=reg_pkg.keywords or [],
                )

    except Exception as exc:
        registry_error = str(exc)
        registry_status = RegistryStatus(
            available=False,
            error=f"Registry unavailable: {registry_error}",
        )
        log.warning(f"Registry fetch failed for packages summary: {exc}")

    packages_list = sorted(
        packages_map.values(),
        key=lambda p: (not p.installed, p.identifier.lower()),
    )

    return PackagesSummaryResponse(
        packages=packages_list,
        total=len(packages_list),
        installed_count=installed_count,
        registry_status=registry_status,
    )


@router.get("/api/packages", response_model=PackagesResponse)
async def get_packages(
    paths: Optional[str] = Query(
        None,
        description="Comma-separated list of paths to scan for projects. If not provided, uses configured workspace paths.",
    ),
    project_root: Optional[str] = Query(
        None, description="Filter to packages installed in a specific project."
    ),
    include_registry: bool = Query(
        True, description="Include latest_version and metadata from registry."
    ),
    ctx: AppContext = Depends(get_ctx),
):
    if paths:
        scan_paths = [Path(p.strip()) for p in paths.split(",")]
    else:
        scan_paths = ctx.workspace_paths

    if not scan_paths:
        return PackagesResponse(packages=[], total=0)

    packages_map = package_manager.get_all_installed_packages(scan_paths)
    if include_registry:
        packages_map = package_manager.enrich_packages_with_registry(packages_map)

    if project_root:
        packages_list = [
            pkg for pkg in packages_map.values() if project_root in pkg.installed_in
        ]
    else:
        packages_list = list(packages_map.values())

    packages_list.sort(key=lambda p: p.identifier.lower())

    return PackagesResponse(packages=packages_list, total=len(packages_list))


@router.get("/api/packages/{package_id:path}/details", response_model=PackageDetails)
async def get_package_details(
    package_id: str,
    paths: Optional[str] = Query(None),
    ctx: AppContext = Depends(get_ctx),
):
    details = package_manager.get_package_details_from_registry(package_id)

    if not details:
        raise HTTPException(
            status_code=404,
            detail=f"Package not found in registry: {package_id}",
        )

    if paths:
        scan_paths = [Path(p.strip()) for p in paths.split(",")]
    else:
        scan_paths = ctx.workspace_paths

    if scan_paths:
        packages_map = package_manager.get_all_installed_packages(scan_paths)
        if package_id in packages_map:
            installed = packages_map[package_id]
            details.installed = True
            details.installed_version = installed.version
            details.installed_in = installed.installed_in

    return details


@router.get("/api/packages/{package_id:path}", response_model=PackageInfo)
async def get_package(
    package_id: str,
    paths: Optional[str] = Query(None),
    ctx: AppContext = Depends(get_ctx),
):
    if paths:
        scan_paths = [Path(p.strip()) for p in paths.split(",")]
    else:
        scan_paths = ctx.workspace_paths

    packages_map = package_manager.get_all_installed_packages(scan_paths)
    if package_id in packages_map:
        return packages_map[package_id]

    parts = package_id.split("/")
    if len(parts) == 2:
        publisher, name = parts
    else:
        publisher = "unknown"
        name = package_id

    return PackageInfo(
        identifier=package_id,
        name=name,
        publisher=publisher,
        installed=False,
    )


@router.post("/api/packages/install", response_model=PackageActionResponse)
async def install_package(
    request: PackageActionRequest,
    background_tasks: BackgroundTasks,
):
    project_path = Path(request.project_root)
    if not project_path.exists():
        raise HTTPException(
            status_code=400,
            detail=f"Project path does not exist: {request.project_root}",
        )

    if not (project_path / "ato.yaml").exists():
        raise HTTPException(
            status_code=400,
            detail=f"No ato.yaml found in: {request.project_root}",
        )

    with package_manager._package_op_lock:
        op_id = package_manager.next_package_op_id("pkg-install")
        package_manager._active_package_ops[op_id] = {
            "action": "install",
            "status": "running",
            "package": request.package_identifier,
            "project_root": request.project_root,
            "error": None,
        }

    cmd = ["ato", "add", request.package_identifier]
    if request.version:
        cmd.append(f"@{request.version}")

    def run_install():
        try:
            result = subprocess.run(
                cmd,
                cwd=request.project_root,
                capture_output=True,
                text=True,
                timeout=120,
            )
            with package_manager._package_op_lock:
                if result.returncode == 0:
                    package_manager._active_package_ops[op_id]["status"] = "success"
                else:
                    package_manager._active_package_ops[op_id]["status"] = "failed"
                    package_manager._active_package_ops[op_id]["error"] = result.stderr[:500]
        except Exception as exc:
            with package_manager._package_op_lock:
                package_manager._active_package_ops[op_id]["status"] = "failed"
                package_manager._active_package_ops[op_id]["error"] = str(exc)

    background_tasks.add_task(run_install)

    return PackageActionResponse(
        success=True,
        message=f"Installing {request.package_identifier}...",
        action="install",
    )


@router.post("/api/packages/remove", response_model=PackageActionResponse)
async def remove_package(
    request: PackageActionRequest,
    background_tasks: BackgroundTasks,
):
    project_path = Path(request.project_root)
    if not project_path.exists():
        raise HTTPException(
            status_code=400,
            detail=f"Project path does not exist: {request.project_root}",
        )

    with package_manager._package_op_lock:
        op_id = package_manager.next_package_op_id("pkg-remove")
        package_manager._active_package_ops[op_id] = {
            "action": "remove",
            "status": "running",
            "package": request.package_identifier,
            "project_root": request.project_root,
            "error": None,
        }

    cmd = ["ato", "remove", request.package_identifier]

    def run_remove():
        try:
            result = subprocess.run(
                cmd,
                cwd=request.project_root,
                capture_output=True,
                text=True,
                timeout=60,
            )
            with package_manager._package_op_lock:
                if result.returncode == 0:
                    package_manager._active_package_ops[op_id]["status"] = "success"
                else:
                    package_manager._active_package_ops[op_id]["status"] = "failed"
                    package_manager._active_package_ops[op_id]["error"] = result.stderr[:500]
        except Exception as exc:
            with package_manager._package_op_lock:
                package_manager._active_package_ops[op_id]["status"] = "failed"
                package_manager._active_package_ops[op_id]["error"] = str(exc)

    background_tasks.add_task(run_remove)

    return PackageActionResponse(
        success=True,
        message=f"Removing {request.package_identifier}...",
        action="remove",
    )
