"""Package-related endpoints helpers and logic."""

from __future__ import annotations

import asyncio
import logging
import os
import re
import threading
import time
from pathlib import Path
from typing import Optional

from fastapi import BackgroundTasks, HTTPException

from atopile.dataclasses import (
    AppContext,
    PackageActionRequest,
    PackageActionResponse,
    PackageArtifact,
    PackageAuthor,
    PackageDependency,
    PackageDetails,
    PackageFileHashes,
    PackageImportStatement,
    PackageInfo,
    PackageLayout,
    PackagesResponse,
    PackagesSummaryResponse,
    PackageSummaryItem,
    PackageVersion,
    RegistrySearchResponse,
    RegistryStatus,
)
from atopile.model.model_state import model_state
from atopile.server.connections import server_state
from atopile.server.core import packages as core_packages
from faebryk.libs.backend.packages.api import PackagesAPIClient


def _get_api() -> PackagesAPIClient:
    """Get a fresh API client instance."""
    return PackagesAPIClient()


log = logging.getLogger(__name__)

# Registry cache
_registry_cache: dict[str, list[PackageInfo]] = {}
_registry_cache_time: float = 0.0
_REGISTRY_CACHE_TTL = int(os.getenv("ATOPILE_REGISTRY_CACHE_TTL", "0"))

_SEMVER_RE = re.compile(r"^v?\d+\.\d+\.\d+(?:[-+].*)?$")

# Lock to prevent concurrent refresh_packages_state calls
_refresh_lock: asyncio.Lock | None = None


def _get_refresh_lock() -> asyncio.Lock:
    """Get or create the refresh lock (must be called from async context)."""
    global _refresh_lock
    if _refresh_lock is None:
        _refresh_lock = asyncio.Lock()
    return _refresh_lock


# Track active package operations
_active_package_ops: dict[str, dict[str, object]] = {}
_package_op_counter = 0
_package_op_lock = threading.Lock()


def _cache_get(key: str) -> list[PackageInfo] | None:
    if _REGISTRY_CACHE_TTL <= 0:
        return None
    now = time.time()
    if key in _registry_cache and (now - _registry_cache_time) < _REGISTRY_CACHE_TTL:
        return _registry_cache[key]
    return None


def _cache_set(key: str, packages: list[PackageInfo]) -> None:
    if _REGISTRY_CACHE_TTL <= 0:
        return
    global _registry_cache_time
    _registry_cache[key] = packages
    _registry_cache_time = time.time()


def version_is_newer(installed: str | None, latest: str | None) -> bool:
    """
    Check if latest version is newer than installed version.

    Simple semver comparison - handles common version formats.
    Returns False if either version is None or comparison fails.
    """
    if not installed or not latest:
        return False

    try:
        installed = installed.lstrip("v")
        latest = latest.lstrip("v")

        def parse_version(v: str) -> tuple[int, ...]:
            base = v.split("-")[0].split("+")[0]
            return tuple(int(x) for x in base.split(".") if x.isdigit())

        installed_parts = parse_version(installed)
        latest_parts = parse_version(latest)

        max_len = max(len(installed_parts), len(latest_parts))
        installed_padded = installed_parts + (0,) * (max_len - len(installed_parts))
        latest_padded = latest_parts + (0,) * (max_len - len(latest_parts))

        return latest_padded > installed_padded

    except (ValueError, AttributeError):
        return False


def next_package_op_id(prefix: str) -> str:
    """Reserve and return a new package operation id."""
    global _package_op_counter
    with _package_op_lock:
        _package_op_counter += 1
        op_id = f"{prefix}-{_package_op_counter}-{int(time.time())}"
    return op_id


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


def get_installed_packages_for_workspace(workspace_path: Path | None):
    """
    Get all installed packages for the workspace path.

    Returns a dict of package_identifier -> PackageInfo.
    """
    if not workspace_path:
        return {}
    return core_packages.get_all_installed_packages([workspace_path])


def search_registry_packages(query: str) -> list[PackageInfo]:
    """
    Search the package registry for packages matching the query.

    Uses the PackagesAPIClient to query the registry API.
    Results are cached for 5 minutes.
    """
    if not query.strip():
        cache_key = "all"
        cached = _cache_get(cache_key)
        if cached is not None:
            log.debug(f"[registry] Cache HIT for all-packages: {len(cached)} packages")
            return cached

        packages = get_all_registry_packages()
        _cache_set(cache_key, packages)
        return packages

    cache_key = f"search:{query}"
    cached = _cache_get(cache_key)
    if cached is not None:
        log.debug(f"[registry] Cache HIT for '{query}': {len(cached)} packages")
        return cached

    try:
        result = _get_api().query_packages(query)
        log.debug(f"[registry] Fetched {len(result.packages)} packages for '{query}'")

        packages: list[PackageInfo] = []
        for pkg in result.packages:
            parts = pkg.identifier.split("/")
            if len(parts) == 2:
                publisher, name = parts
            else:
                publisher = "unknown"
                name = pkg.identifier

            packages.append(
                PackageInfo(
                    identifier=pkg.identifier,
                    name=name,
                    publisher=publisher,
                    latest_version=pkg.version,
                    summary=pkg.summary,
                    description=pkg.summary,
                    homepage=pkg.homepage,
                    repository=pkg.repository,
                    installed=False,
                    installed_in=[],
                )
            )

        _cache_set(cache_key, packages)
        return packages

    except Exception as exc:
        log.warning(f"Failed to search registry: {exc}")
        return []


def get_all_registry_packages() -> list[PackageInfo]:
    """
    Get all packages from the registry.
    """
    try:
        api = PackagesAPIClient()
        result = api.get_all_packages()
        log.debug(f"[registry] Fetched {len(result.packages)} packages from registry")

        packages: list[PackageInfo] = []
        for pkg in result.packages:
            parts = pkg.identifier.split("/")
            if len(parts) == 2:
                publisher, name = parts
            else:
                publisher = "unknown"
                name = pkg.identifier

            packages.append(
                PackageInfo(
                    identifier=pkg.identifier,
                    name=name,
                    publisher=publisher,
                    latest_version=pkg.version,
                    summary=pkg.summary,
                    description=pkg.summary,
                    homepage=pkg.homepage,
                    repository=pkg.repository,
                    installed=False,
                    installed_in=[],
                )
            )

        return packages

    except Exception as exc:
        log.warning(f"Failed to fetch all packages from registry: {exc}")
        return []


async def get_all_registry_packages_async() -> list[PackageInfo]:
    """
    Async version of get_all_registry_packages.

    Runs the API call in a thread pool to avoid blocking the event loop.
    """
    # Run the synchronous function in a thread to avoid blocking
    return await asyncio.to_thread(get_all_registry_packages)


async def enrich_packages_with_registry_async(
    packages: dict[str, PackageInfo],
) -> dict[str, PackageInfo]:
    """
    Async version of enrich_packages_with_registry.

    Fetches latest_version, summary, homepage, etc. from the registry
    for each installed package using parallel HTTP requests.
    """
    if not packages:
        return packages

    registry_data = await get_all_registry_packages_async()
    registry_map: dict[str, PackageInfo] = {
        pkg.identifier: pkg for pkg in registry_data
    }

    enriched: dict[str, PackageInfo] = {}
    for identifier, pkg in packages.items():
        if identifier in registry_map:
            reg = registry_map[identifier]
            enriched[identifier] = PackageInfo(
                identifier=pkg.identifier,
                name=pkg.name,
                publisher=pkg.publisher,
                version=pkg.version,
                latest_version=reg.latest_version,
                description=reg.description,
                summary=reg.summary,
                homepage=reg.homepage,
                repository=reg.repository,
                license=reg.license,
                installed=True,
                installed_in=pkg.installed_in,
            )
        else:
            enriched[identifier] = pkg

    return enriched


def get_package_details_from_registry(
    identifier: str, version: str | None = None
) -> PackageDetails | None:
    """
    Get detailed package information from the registry.

    Fetches:
    - Full package info with stats (downloads)
    - List of releases (versions)
    - Dependencies
    """
    if version and not _SEMVER_RE.match(version):
        version = None

    try:
        api = _get_api()
        pkg_response = api.get_package(identifier, version=version)
        releases = api.get_package_releases(identifier)
        pkg_info = pkg_response.info
        readme = getattr(pkg_response, "readme", None)

        parts = identifier.split("/")
        if len(parts) == 2:
            publisher, name = parts
        else:
            publisher = "unknown"
            name = identifier

        versions = []
        for rel in releases:
            released_at = getattr(rel, "released_at", None)
            if hasattr(released_at, "isoformat"):
                released_at = released_at.isoformat()
            versions.append(
                PackageVersion(
                    version=getattr(rel, "version", "unknown"),
                    released_at=released_at if isinstance(released_at, str) else None,
                    requires_atopile=getattr(rel, "requires_atopile", None),
                    size=getattr(rel, "size", None),
                )
            )

        versions.sort(key=lambda v: v.released_at or "", reverse=True)

        stats = pkg_info.stats if hasattr(pkg_info, "stats") else None

        # Extract dependencies from the package info
        dependencies = []
        requires = getattr(getattr(pkg_info, "dependencies", None), "requires", [])
        for dep in requires or []:
            dependencies.append(
                PackageDependency(
                    identifier=dep.identifier,
                    version=getattr(dep, "release", None),
                )
            )

        authors = []
        for author in getattr(pkg_info, "authors", []) or []:
            authors.append(
                PackageAuthor(
                    name=getattr(author, "name", ""),
                    email=getattr(author, "email", None),
                )
            )

        artifacts = []
        artifacts_info = getattr(pkg_info, "artifacts", None)
        for artifact in getattr(artifacts_info, "artifacts", []) or []:
            artifacts.append(
                PackageArtifact(
                    filename=artifact.filename,
                    url=artifact.url,
                    size=artifact.size,
                    hashes=PackageFileHashes(sha256=artifact.hashes.sha256),
                    build_name=getattr(artifact, "build_name", None),
                )
            )

        layouts = []
        layouts_info = getattr(pkg_info, "layouts", None)
        for layout in getattr(layouts_info, "layouts", []) or []:
            layouts.append(
                PackageLayout(
                    build_name=layout.build_name,
                    url=layout.url,
                )
            )

        import_statements = []
        for stmt in getattr(pkg_info, "import_statements", []) or []:
            import_statements.append(
                PackageImportStatement(
                    build_name=stmt.build_name,
                    import_statement=stmt.import_statement,
                )
            )

        created_at = getattr(pkg_info, "created_at", None)
        if hasattr(created_at, "isoformat"):
            created_at = created_at.isoformat()
        released_at = getattr(pkg_info, "released_at", None)
        if hasattr(released_at, "isoformat"):
            released_at = released_at.isoformat()

        return PackageDetails(
            identifier=identifier,
            name=name,
            publisher=publisher,
            version=pkg_info.version,
            created_at=created_at if isinstance(created_at, str) else None,
            released_at=released_at if isinstance(released_at, str) else None,
            authors=authors,
            summary=pkg_info.summary,
            description=pkg_info.summary,
            homepage=pkg_info.homepage,
            repository=pkg_info.repository,
            license=pkg_info.license if hasattr(pkg_info, "license") else None,
            downloads=stats.total_downloads if stats else None,
            downloads_this_week=stats.this_week_downloads if stats else None,
            downloads_this_month=stats.this_month_downloads if stats else None,
            versions=versions,
            version_count=len(versions),
            dependencies=dependencies,
            readme=readme,
            builds=getattr(pkg_info, "builds", None),
            artifacts=artifacts,
            layouts=layouts,
            import_statements=import_statements,
        )

    except Exception as exc:
        log.warning(f"Failed to get package details for {identifier}: {exc}")
        return None


def enrich_packages_with_registry(
    packages: dict[str, PackageInfo],
) -> dict[str, PackageInfo]:
    """
    Enrich installed packages with metadata from the registry.

    Fetches latest_version, summary, homepage, etc. from the registry
    for each installed package.
    """
    if not packages:
        return packages

    registry_data = get_all_registry_packages()
    registry_map: dict[str, PackageInfo] = {
        pkg.identifier: pkg for pkg in registry_data
    }

    enriched: dict[str, PackageInfo] = {}
    for identifier, pkg in packages.items():
        if identifier in registry_map:
            reg = registry_map[identifier]
            enriched[identifier] = PackageInfo(
                identifier=pkg.identifier,
                name=pkg.name,
                publisher=pkg.publisher,
                version=pkg.version,
                latest_version=reg.latest_version,
                description=reg.description,
                summary=reg.summary,
                homepage=reg.homepage,
                repository=reg.repository,
                license=reg.license,
                installed=True,
                installed_in=pkg.installed_in,
            )
        else:
            enriched[identifier] = pkg

    return enriched


def _fetch_packages_sync(
    scan_path: Path | None,
) -> tuple[list, str | None]:
    """
    Sync helper that fetches installed and registry packages.
    Returns (state_packages_list, registry_error).
    """
    from atopile.dataclasses import PackageInfo as StatePackageInfo

    packages_map: dict[str, StatePackageInfo] = {}
    registry_error: str | None = None

    if scan_path:
        installed = get_installed_packages_for_workspace(scan_path)
        for pkg in installed.values():
            packages_map[pkg.identifier] = StatePackageInfo(
                identifier=pkg.identifier,
                name=pkg.name,
                publisher=pkg.publisher,
                version=pkg.version,
                installed=True,
                installed_in=pkg.installed_in,
            )

    try:
        registry_packages = get_all_registry_packages()
        log.info(
            f"[refresh_packages_state] Registry returned {len(registry_packages)} packages"  # noqa: E501
        )

        for reg_pkg in registry_packages:
            if reg_pkg.identifier in packages_map:
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
                    has_update=version_is_newer(
                        existing.version, reg_pkg.latest_version
                    ),
                    downloads=reg_pkg.downloads,
                    version_count=reg_pkg.version_count,
                    keywords=reg_pkg.keywords or [],
                )
            else:
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
        log.warning(f"[refresh_packages_state] Registry fetch failed: {exc}")

    state_packages = sorted(
        packages_map.values(),
        key=lambda p: (not p.installed, p.identifier.lower()),
    )

    return list(state_packages), registry_error


async def refresh_packages_state(
    scan_path: Path | None = None,
) -> None:
    """Refresh packages and emit a packages_changed event."""
    lock = _get_refresh_lock()

    # Skip if another refresh is already in progress
    if lock.locked():
        log.debug("[refresh_packages_state] Skipping - refresh already in progress")
        return

    async with lock:
        if scan_path is None:
            scan_path = model_state.workspace_path

        # Run blocking I/O in thread pool to avoid blocking event loop
        state_packages, registry_error = await asyncio.to_thread(
            _fetch_packages_sync, scan_path
        )

        await server_state.emit_event(
            "packages_changed",
            {"error": registry_error, "total": len(state_packages)},
        )
        log.info("Refreshed packages: %d packages", len(state_packages))


async def refresh_installed_packages_state(
    scan_path: Path | None = None,
) -> None:
    """Refresh installed package flags without hitting the registry."""
    if scan_path is None:
        scan_path = model_state.workspace_path

    if not scan_path:
        await server_state.emit_event("packages_changed")
        return

    await asyncio.to_thread(core_packages.get_all_installed_packages, [scan_path])
    await server_state.emit_event("packages_changed")


def handle_search_registry(
    query: str,
    scan_path: Path | None,
) -> RegistrySearchResponse:
    registry_packages = search_registry_packages(query)

    if scan_path:
        installed_map = get_installed_packages_for_workspace(scan_path)
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


def handle_packages_summary(
    scan_path: Path | None,
) -> PackagesSummaryResponse:
    packages_map: dict[str, PackageSummaryItem] = {}
    installed_count = 0

    if scan_path:
        installed = get_installed_packages_for_workspace(scan_path)
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

    try:
        registry_packages = get_all_registry_packages()
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
                    has_update=version_is_newer(
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
        registry_status = RegistryStatus(
            available=False,
            error=f"Registry unavailable: {exc}",
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


def handle_get_packages(
    scan_path: Path | None,
    project_root: str | None,
    include_registry: bool,
) -> PackagesResponse:
    if not scan_path:
        return PackagesResponse(packages=[], total=0)

    packages_map = get_installed_packages_for_workspace(scan_path)
    if include_registry:
        packages_map = enrich_packages_with_registry(packages_map)

    if project_root:
        packages_list = [
            pkg for pkg in packages_map.values() if project_root in pkg.installed_in
        ]
    else:
        packages_list = list(packages_map.values())

    packages_list.sort(key=lambda p: p.identifier.lower())

    return PackagesResponse(packages=packages_list, total=len(packages_list))


def handle_get_package_details(
    package_id: str,
    scan_path: Path | None,
    ctx: AppContext,
    version: str | None = None,
) -> PackageDetails:
    details = get_package_details_from_registry(package_id, version=version)

    if not details:
        raise HTTPException(
            status_code=404,
            detail=f"Package not found in registry: {package_id}",
        )

    if scan_path is None:
        scan_path = ctx.workspace_path

    if scan_path:
        packages_map = get_installed_packages_for_workspace(scan_path)
        if package_id in packages_map:
            installed = packages_map[package_id]
            details.installed = True
            details.installed_version = installed.version
            details.installed_in = installed.installed_in

    return details


def handle_get_package_info(
    package_id: str,
    scan_path: Path | None,
    ctx: AppContext,
) -> PackageInfo:
    if scan_path is None:
        scan_path = ctx.workspace_path

    packages_map = get_installed_packages_for_workspace(scan_path)
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


def handle_install_package(
    request: PackageActionRequest,
    background_tasks: BackgroundTasks,
) -> PackageActionResponse:
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

    with _package_op_lock:
        op_id = next_package_op_id("pkg-install")
        _active_package_ops[op_id] = {
            "action": "install",
            "status": "running",
            "package": request.package_identifier,
            "project_root": request.project_root,
            "error": None,
        }

    def run_install():
        try:
            with _package_op_lock:
                try:
                    core_packages.install_package_to_project(
                        project_path, request.package_identifier, request.version
                    )
                    _active_package_ops[op_id]["status"] = "success"
                except Exception as exc:
                    _active_package_ops[op_id]["status"] = "failed"
                    _active_package_ops[op_id]["error"] = (
                        str(exc)[:500] or "ato add failed"
                    )
        except Exception as exc:
            with _package_op_lock:
                _active_package_ops[op_id]["status"] = "failed"
                _active_package_ops[op_id]["error"] = str(exc)

    background_tasks.add_task(run_install)

    return PackageActionResponse(
        success=True,
        message=f"Installing {request.package_identifier}...",
        action="install",
    )


def handle_remove_package(
    request: PackageActionRequest,
    background_tasks: BackgroundTasks,
) -> PackageActionResponse:
    project_path = Path(request.project_root)
    if not project_path.exists():
        raise HTTPException(
            status_code=400,
            detail=f"Project path does not exist: {request.project_root}",
        )

    with _package_op_lock:
        op_id = next_package_op_id("pkg-remove")
        _active_package_ops[op_id] = {
            "action": "remove",
            "status": "running",
            "package": request.package_identifier,
            "project_root": request.project_root,
            "error": None,
        }

    def run_remove():
        try:
            with _package_op_lock:
                try:
                    core_packages.remove_package_from_project(
                        project_path, request.package_identifier
                    )
                    _active_package_ops[op_id]["status"] = "success"
                except Exception as exc:
                    _active_package_ops[op_id]["status"] = "failed"
                    _active_package_ops[op_id]["error"] = (
                        str(exc)[:500] or "ato remove failed"
                    )
        except Exception as exc:
            with _package_op_lock:
                _active_package_ops[op_id]["status"] = "failed"
                _active_package_ops[op_id]["error"] = str(exc)

    background_tasks.add_task(run_remove)

    return PackageActionResponse(
        success=True,
        message=f"Removing {request.package_identifier}...",
        action="remove",
    )


def resolve_scan_path(
    ctx: AppContext,
    path: Optional[str],
) -> Path | None:
    if path:
        return Path(path.strip())
    return ctx.workspace_paths[0] if ctx.workspace_paths else None


__all__ = [
    "_active_package_ops",
    "_package_op_lock",
    "enrich_packages_with_registry",
    "get_all_installed_packages",
    "get_all_registry_packages",
    "get_installed_packages_for_project",
    "get_installed_packages_for_workspace",
    "get_package_details_from_registry",
    "handle_get_package_details",
    "handle_get_package_info",
    "handle_get_packages",
    "handle_install_package",
    "handle_packages_summary",
    "handle_remove_package",
    "handle_search_registry",
    "next_package_op_id",
    "refresh_packages_state",
    "resolve_scan_path",
    "search_registry_packages",
    "version_is_newer",
]
