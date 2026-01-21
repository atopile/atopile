"""
Package registry access and caching.

This module isolates external API calls for package metadata.
"""

from __future__ import annotations

import logging
import os
import string
import time

from ..schemas.package import PackageDetails, PackageInfo, PackageVersion

log = logging.getLogger(__name__)

# Registry cache
_registry_cache: dict[str, list[PackageInfo]] = {}
_registry_cache_time: float = 0.0
_REGISTRY_CACHE_TTL = int(os.getenv("ATOPILE_REGISTRY_CACHE_TTL", "0"))

# TODO: HACK - Registry API doesn't support listing all packages (empty query returns 0).
# Workaround: query multiple search terms and merge results to approximate "get all".
# These terms were empirically chosen for maximum coverage (~149 packages as of 2025-01).
# Proper fix: add a /v1/packages/list endpoint to the registry API.
_REGISTRY_SEARCH_TERMS = list(string.ascii_lowercase + string.digits)


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


def search_registry_packages(query: str) -> list[PackageInfo]:
    """
    Search the package registry for packages matching the query.

    Uses the PackagesAPIClient to query the registry API.
    Results are cached for 5 minutes.
    """
    cache_key = f"search:{query}"
    cached = _cache_get(cache_key)
    if cached is not None:
        log.debug(f"[registry] Cache HIT for '{query}': {len(cached)} packages")
        return cached

    try:
        from faebryk.libs.backend.packages.api import PackagesAPIClient

        api = PackagesAPIClient()
        result = api.query_packages(query)
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

    except Exception as e:
        log.warning(f"Failed to search registry: {e}")
        return []


def get_all_registry_packages() -> list[PackageInfo]:
    """
    Get all packages from the registry by querying multiple search terms.

    The registry API requires a search term (empty/wildcard returns 0 results).
    This function queries multiple terms and merges results to get all packages.
    Results are cached for 5 minutes.
    """
    cache_key = "all_packages"
    cached = _cache_get(cache_key)
    if cached is not None:
        log.debug(f"[registry] Cache HIT for all packages: {len(cached)} packages")
        return cached

    packages_map: dict[str, PackageInfo] = {}
    for term in _REGISTRY_SEARCH_TERMS:
        try:
            results = search_registry_packages(term)
            for pkg in results:
                if pkg.identifier not in packages_map:
                    packages_map[pkg.identifier] = pkg
        except Exception as e:
            log.warning(f"Failed to search registry for '{term}': {e}")

    packages = list(packages_map.values())
    log.info(f"[registry] Merged {len(packages)} unique packages from registry")
    _cache_set(cache_key, packages)
    return packages


def get_package_details_from_registry(identifier: str) -> PackageDetails | None:
    """
    Get detailed package information from the registry.

    Fetches:
    - Full package info with stats (downloads)
    - List of releases (versions)
    """
    try:
        from faebryk.libs.backend.packages.api import PackagesAPIClient

        api = PackagesAPIClient()

        pkg_response = api.get_package(identifier)
        pkg_info = pkg_response.info

        releases_response = api._get(f"/v1/package/{identifier}/releases")
        releases_data = releases_response.json()
        releases = releases_data.get("releases", [])

        parts = identifier.split("/")
        if len(parts) == 2:
            publisher, name = parts
        else:
            publisher = "unknown"
            name = identifier

        versions = []
        for rel in releases:
            released_at = rel.get("released_at")
            if isinstance(released_at, str):
                pass
            elif hasattr(released_at, "isoformat"):
                released_at = released_at.isoformat()
            else:
                released_at = None

            versions.append(
                PackageVersion(
                    version=rel.get("version", "unknown"),
                    released_at=released_at,
                    requires_atopile=rel.get("requires_atopile"),
                    size=rel.get("size"),
                )
            )

        versions.sort(key=lambda v: v.released_at or "", reverse=True)

        stats = pkg_info.stats if hasattr(pkg_info, "stats") else None

        return PackageDetails(
            identifier=identifier,
            name=name,
            publisher=publisher,
            version=pkg_info.version,
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
        )

    except Exception as e:
        log.warning(f"Failed to get package details for {identifier}: {e}")
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
    registry_map: dict[str, PackageInfo] = {pkg.identifier: pkg for pkg in registry_data}

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
