"""Package-related API routes."""

from __future__ import annotations

import asyncio
import os
from typing import Optional
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from starlette.responses import StreamingResponse

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


def _asset_proxy_allowed_hosts() -> set[str]:
    allowed = set(
        host.strip()
        for host in os.getenv("ATOPILE_PACKAGES_ASSET_HOSTS", "").split(",")
        if host.strip()
    )
    if allowed:
        return allowed
    # Default allowlist for common CDN domains if not explicitly configured.
    return {"cloudfront.net"}


def _is_host_allowed(host: str) -> bool:
    allowed = _asset_proxy_allowed_hosts()
    if not allowed:
        return os.getenv("ATOPILE_ALLOW_UNSAFE_ASSET_PROXY", "").lower() in {
            "1",
            "true",
            "yes",
        }
    return host in allowed or any(
        host.endswith(f".{allowed_host}") for allowed_host in allowed
    )


def _content_type_for_filename(filename: str | None) -> str | None:
    if not filename:
        return None
    lower = filename.lower()
    if lower.endswith(".kicad_pcb"):
        return "text/plain"
    if lower.endswith(".glb"):
        return "model/gltf-binary"
    return None


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
    version: Optional[str] = Query(None),
    ctx: AppContext = Depends(get_ctx),
):
    scan_path = packages_domain.resolve_scan_path(ctx, path)
    return await asyncio.to_thread(
        packages_domain.handle_get_package_details, package_id, scan_path, ctx, version
    )


@router.get("/api/packages/proxy")
async def proxy_package_asset(url: str, filename: str | None = None):
    return await _proxy_package_asset(url, filename)


@router.get("/api/packages/proxy/{filename:path}")
async def proxy_package_asset_named(filename: str, url: str):
    return await _proxy_package_asset(url, filename)


async def _proxy_package_asset(url: str, filename: str | None):
    parsed = urlparse(url)
    if parsed.scheme not in {"https", "http"} or not parsed.netloc:
        raise HTTPException(status_code=400, detail="Invalid asset URL")
    if not _is_host_allowed(parsed.netloc):
        raise HTTPException(status_code=403, detail="Asset host not allowed")
    headers: dict[str, str] = {}

    async def _iter_bytes():
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream("GET", url) as response:
                if response.status_code >= 400:
                    raise HTTPException(
                        status_code=response.status_code, detail="Asset fetch failed"
                    )
                content_type = response.headers.get(
                    "content-type"
                ) or _content_type_for_filename(filename)
                if content_type:
                    headers["content-type"] = content_type
                cache_control = response.headers.get("cache-control")
                if cache_control:
                    headers["cache-control"] = cache_control
                content_length = response.headers.get("content-length")
                if content_length:
                    headers["content-length"] = content_length
                async for chunk in response.aiter_bytes():
                    yield chunk

    return StreamingResponse(_iter_bytes(), headers=headers)


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
