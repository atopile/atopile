"""Package-related endpoints helpers and logic."""

from __future__ import annotations

import asyncio
import logging
import re
import threading
import time
from pathlib import Path
from typing import Optional

import yaml
from fastapi import BackgroundTasks, HTTPException

from atopile.cli import install as cli_install
from atopile.dataclasses import (
    AppContext,
    InstalledPackage,
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
    SyncPackagesRequest,
    SyncPackagesResponse,
)
from atopile.errors import UserException as AtopileUserException
from atopile.server.connections import server_state
from atopile.server.domains import projects as projects_domain
from faebryk.libs.backend.packages.api import PackagesAPIClient


def _get_api() -> PackagesAPIClient:
    """Get a fresh API client instance."""
    return PackagesAPIClient()


log = logging.getLogger(__name__)

_SEMVER_RE = re.compile(r"^v?\d+\.\d+\.\d+(?:[-+].*)?$")

# Track active package operations
_active_package_ops: dict[str, dict[str, object]] = {}
_package_op_counter = 0
_package_op_lock = threading.Lock()


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


def _format_install_error(exc: Exception) -> str:
    if isinstance(exc, AtopileUserException):
        message = getattr(exc, "message", "") or str(exc)
        return message or "ato add/remove failed"
    return str(exc) or "ato add/remove failed"


def get_installed_packages_for_project(project_root: Path) -> list[InstalledPackage]:
    """
    Read installed packages from a project's ato.yaml dependencies section.
    """
    ato_yaml = project_root / "ato.yaml"
    if not ato_yaml.exists():
        return []

    try:
        with open(ato_yaml, "r") as f:
            data = yaml.safe_load(f)

        if not data:
            return []

        packages: list[InstalledPackage] = []
        dependencies = data.get("dependencies", [])

        if isinstance(dependencies, list):
            for dep in dependencies:
                if isinstance(dep, dict):
                    identifier = dep.get("identifier", "")
                    version = dep.get("release", dep.get("version", "unknown"))
                    if identifier:
                        packages.append(
                            InstalledPackage(
                                identifier=identifier,
                                version=version,
                                project_root=str(project_root),
                            )
                        )
        elif isinstance(dependencies, dict):
            for dep_id, dep_info in dependencies.items():
                if isinstance(dep_info, str):
                    version = dep_info
                elif isinstance(dep_info, dict):
                    version = dep_info.get("version", "unknown")
                else:
                    continue

                packages.append(
                    InstalledPackage(
                        identifier=dep_id,
                        version=version,
                        project_root=str(project_root),
                    )
                )

        return packages

    except Exception as e:
        log.warning(f"Failed to read packages from {ato_yaml}: {e}")
        return []


def get_all_installed_packages(paths: list[Path]) -> dict[str, PackageInfo]:
    """
    Get all installed packages across all projects in the given paths.
    """
    projects = projects_domain.discover_projects_in_paths(paths)
    return get_all_installed_packages_from_projects(projects)


def get_all_installed_packages_from_projects(
    projects: list,
) -> dict[str, PackageInfo]:
    """Get all installed packages from pre-discovered projects."""
    packages_map: dict[str, PackageInfo] = {}

    for project in projects:
        project_root = Path(project.root)
        installed = get_installed_packages_for_project(project_root)

        for pkg in installed:
            if pkg.identifier not in packages_map:
                parts = pkg.identifier.split("/")
                if len(parts) == 2:
                    publisher, name = parts
                else:
                    publisher = "unknown"
                    name = pkg.identifier

                packages_map[pkg.identifier] = PackageInfo(
                    identifier=pkg.identifier,
                    name=name,
                    publisher=publisher,
                    version=pkg.version,
                    installed=True,
                    installed_in=[project.root],
                )
            else:
                if project.root not in packages_map[pkg.identifier].installed_in:
                    packages_map[pkg.identifier].installed_in.append(project.root)

    return packages_map


def install_package_to_project(
    project_root: Path, package_identifier: str, version: str | None = None
) -> None:
    """Install or update a package in a project via the internal CLI implementation."""
    pkg_spec = f"{package_identifier}@{version}" if version else package_identifier
    try:
        cli_install.add([pkg_spec], path=project_root)
    except Exception as exc:
        raise RuntimeError(_format_install_error(exc)) from exc


def remove_package_from_project(project_root: Path, package_identifier: str) -> None:
    """Remove a package from a project via the internal CLI implementation."""
    try:
        cli_install.remove([package_identifier], path=project_root)
    except Exception as exc:
        raise RuntimeError(_format_install_error(exc)) from exc


def sync_packages_for_project(project_root: Path, force: bool = False) -> None:
    """
    Sync packages for a project - ensure installed versions match manifest.

    Args:
        project_root: Path to the project directory
        force: If True, overwrite locally modified packages without error.
               If False (default), raise error for modified packages.

    Raises:
        RuntimeError: If sync fails (with formatted error message)
        PackageModifiedError: If packages have local modifications and force=False
    """
    from atopile.config import config
    from faebryk.libs.package.meta import PackageModifiedError
    from faebryk.libs.project.dependencies import ProjectDependencies

    # Apply config for this project
    config.apply_options(None, working_dir=project_root)

    try:
        ProjectDependencies(
            install_missing=True,
            clean_unmanaged_dirs=True,
            force_sync=force,
        )
    except PackageModifiedError:
        # Re-raise as-is so the caller can handle it specially
        raise
    except Exception as exc:
        raise RuntimeError(_format_install_error(exc)) from exc


def get_installed_packages_for_workspace(workspace_path: Path | None):
    """
    Get all installed packages for the workspace path.

    Returns a dict of package_identifier -> PackageInfo.
    """
    if not workspace_path:
        return {}
    return get_all_installed_packages([workspace_path])


def search_registry_packages(query: str) -> list[PackageInfo]:
    """Search the package registry for packages matching the query."""
    if not query.strip():
        return get_all_registry_packages()

    try:
        result = _get_api().query_packages(query)

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
                    downloads=pkg.downloads,
                )
            )

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
                    downloads=pkg.downloads,
                )
            )

        return packages

    except Exception as exc:
        log.warning(f"Failed to fetch all packages from registry: {exc}")
        return []


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


async def refresh_packages_state(
    scan_path: Path | None = None,
) -> None:
    """Notify the frontend to refetch package data."""
    await server_state.emit_event("packages_changed")


async def refresh_installed_packages_state(
    scan_path: Path | None = None,
) -> None:
    """Notify the frontend to refetch package data (installed only)."""
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
        key=lambda p: (not p.installed, -(p.downloads or 0), p.identifier.lower()),
    )

    return PackagesSummaryResponse(
        packages=packages_list,
        total=len(packages_list),
        installed_count=installed_count,
        registry_status=registry_status,
    )


def fetch_package_downloads(identifier: str) -> int | None:
    """
    Fetch download count for a single package from the registry.
    Returns None if fetch fails.

    TODO: Remove this when /v1/packages/all includes downloads.
    """
    try:
        api = _get_api()
        pkg_response = api.get_package(identifier)
        pkg_info = pkg_response.info
        stats = pkg_info.stats if hasattr(pkg_info, "stats") else None
        return stats.total_downloads if stats else None
    except Exception as exc:
        log.debug(f"Failed to fetch downloads for {identifier}: {exc}")
        return None


async def enrich_packages_with_downloads(identifiers: list[str]) -> None:
    """
    Background task to fetch downloads for packages and emit updates.
    Fetches in batches to avoid overwhelming the API.

    TODO: Remove this when /v1/packages/all includes downloads.
    """
    if not identifiers:
        return

    # Fetch downloads in small batches
    batch_size = 5
    downloads_map: dict[str, int | None] = {}

    for i in range(0, len(identifiers), batch_size):
        batch = identifiers[i : i + batch_size]

        # Fetch batch concurrently
        results = await asyncio.gather(
            *[asyncio.to_thread(fetch_package_downloads, pkg_id) for pkg_id in batch],
            return_exceptions=True,
        )

        for pkg_id, result in zip(batch, results):
            if isinstance(result, Exception):
                downloads_map[pkg_id] = None
            else:
                downloads_map[pkg_id] = result

        # Emit incremental update after each batch
        batch_updates = {
            pkg_id: downloads_map[pkg_id]
            for pkg_id in batch
            if downloads_map.get(pkg_id) is not None
        }
        if batch_updates:
            await server_state.emit_event(
                "packages_downloads_updated",
                {"downloads": batch_updates},
            )

        # Small delay between batches to be nice to the API
        if i + batch_size < len(identifiers):
            await asyncio.sleep(0.1)


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
                    install_package_to_project(
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
                    remove_package_from_project(
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


def handle_sync_packages(
    request: SyncPackagesRequest,
    background_tasks: BackgroundTasks,
) -> SyncPackagesResponse:
    """
    Handle sync packages request - ensure installed versions match manifest.

    This runs the sync operation in a background task and returns immediately.
    The operation tracks modified packages and handles the PackageModifiedError
    specially to provide useful feedback to the UI.
    """
    from faebryk.libs.package.meta import PackageModifiedError

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
        op_id = next_package_op_id("pkg-sync")
        _active_package_ops[op_id] = {
            "action": "sync",
            "status": "running",
            "project_root": request.project_root,
            "force": request.force,
            "error": None,
            "modified_packages": None,
        }

    def run_sync():
        try:
            sync_packages_for_project(project_path, force=request.force)
            with _package_op_lock:
                _active_package_ops[op_id]["status"] = "success"
        except PackageModifiedError as exc:
            with _package_op_lock:
                _active_package_ops[op_id]["status"] = "blocked"
                _active_package_ops[op_id]["error"] = str(exc)
                _active_package_ops[op_id]["modified_packages"] = exc.modified_files
        except Exception as exc:
            with _package_op_lock:
                _active_package_ops[op_id]["status"] = "failed"
                _active_package_ops[op_id]["error"] = str(exc)[:500] or "sync failed"

    background_tasks.add_task(run_sync)

    force_msg = " (force mode)" if request.force else ""
    return SyncPackagesResponse(
        success=True,
        message=f"Syncing packages{force_msg}...",
        operation_id=op_id,
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
    "get_all_installed_packages_from_projects",
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
    "handle_sync_packages",
    "install_package_to_project",
    "next_package_op_id",
    "refresh_packages_state",
    "remove_package_from_project",
    "resolve_scan_path",
    "search_registry_packages",
    "sync_packages_for_project",
    "version_is_newer",
]
