"""Package-related API routes."""

from __future__ import annotations

import asyncio
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Query

from atopile.dataclasses import (
    AppContext,
    PackageActionRequest,
    PackageActionResponse,
    PackageDetails,
    PackageInfo,
    PackagesResponse,
    PackagesSummaryResponse,
    RegistrySearchResponse,
)
from ..domains import packages as packages_domain
from ..domains.deps import get_ctx

router = APIRouter(tags=["packages"])


@router.get("/api/registry/search", response_model=RegistrySearchResponse)
async def search_registry(
    query: str = Query("", description="Search query. Empty returns popular packages."),
    path: Optional[str] = Query(
        None, description="Path to check installed packages."
    ),
    ctx: AppContext = Depends(get_ctx),
):
    scan_path = packages_domain.resolve_scan_path(ctx, path)
    return await asyncio.to_thread(
        packages_domain.handle_search_registry, query, scan_path
    )


@router.get("/api/packages/summary", response_model=PackagesSummaryResponse)
async def get_packages_summary(
    path: Optional[str] = Query(
        None,
        description=(
            "Path to scan for projects. "
            "If not provided, uses configured workspace path."
        ),
    ),
    ctx: AppContext = Depends(get_ctx),
):
    scan_path = packages_domain.resolve_scan_path(ctx, path)
    return await asyncio.to_thread(packages_domain.handle_packages_summary, scan_path)


@router.get("/api/packages", response_model=PackagesResponse)
async def get_packages(
    path: Optional[str] = Query(
        None,
        description=(
            "Path to scan for projects. "
            "If not provided, uses configured workspace path."
        ),
    ),
    project_root: Optional[str] = Query(
        None, description="Filter to packages installed in a specific project."
    ),
    include_registry: bool = Query(
        True, description="Include latest_version and metadata from registry."
    ),
    ctx: AppContext = Depends(get_ctx),
):
    scan_path = packages_domain.resolve_scan_path(ctx, path)
    return await asyncio.to_thread(
        packages_domain.handle_get_packages, scan_path, project_root, include_registry
    )


@router.get("/api/packages/{package_id:path}/details", response_model=PackageDetails)
async def get_package_details(
    package_id: str,
    path: Optional[str] = Query(None),
    ctx: AppContext = Depends(get_ctx),
):
    scan_path = packages_domain.resolve_scan_path(ctx, path)
    return await asyncio.to_thread(
        packages_domain.handle_get_package_details, package_id, scan_path, ctx
    )


@router.get("/api/packages/{package_id:path}", response_model=PackageInfo)
async def get_package(
    package_id: str,
    path: Optional[str] = Query(None),
    ctx: AppContext = Depends(get_ctx),
):
    scan_path = packages_domain.resolve_scan_path(ctx, path)
    return await asyncio.to_thread(
        packages_domain.handle_get_package_info, package_id, scan_path, ctx
    )


@router.post("/api/packages/install", response_model=PackageActionResponse)
async def install_package(
    request: PackageActionRequest,
    background_tasks: BackgroundTasks,
):
    return await asyncio.to_thread(
        packages_domain.handle_install_package, request, background_tasks
    )


@router.post("/api/packages/remove", response_model=PackageActionResponse)
async def remove_package(
    request: PackageActionRequest,
    background_tasks: BackgroundTasks,
):
    return await asyncio.to_thread(
        packages_domain.handle_remove_package, request, background_tasks
    )
