"""
Thin wrapper around the package registry API.
"""

from __future__ import annotations

from typing import Any

from faebryk.libs.backend.packages.api import PackagesAPIClient


def query_packages(query: str):
    api = PackagesAPIClient()
    return api.query_packages(query)


def get_package(identifier: str, version: str | None = None):
    api = PackagesAPIClient()
    return api.get_package(identifier, version)


def get_package_releases(identifier: str) -> dict[str, Any]:
    api = PackagesAPIClient()
    response = api._get(f"/v1/package/{identifier}/releases")
    return response.json()


__all__ = [
    "get_package",
    "get_package_releases",
    "query_packages",
]
