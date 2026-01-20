"""
Package-related Pydantic schemas.
"""

from typing import Optional

from pydantic import BaseModel, Field


class PackageInfo(BaseModel):
    """Information about a package."""

    identifier: str  # e.g., "atopile/bosch-bme280"
    name: str  # e.g., "bosch-bme280"
    publisher: str  # e.g., "atopile"
    version: Optional[str] = None  # Installed version (if installed)
    latest_version: Optional[str] = None  # Latest available version
    description: Optional[str] = None
    summary: Optional[str] = None
    homepage: Optional[str] = None
    repository: Optional[str] = None
    license: Optional[str] = None
    installed: bool = False
    installed_in: list[str] = Field(default_factory=list)  # List of project roots
    has_update: bool = False
    # Stats from registry (may be None if not fetched)
    downloads: Optional[int] = None
    version_count: Optional[int] = None
    keywords: Optional[list[str]] = None


class PackageVersion(BaseModel):
    """Information about a package version/release."""

    version: str
    released_at: Optional[str] = None
    requires_atopile: Optional[str] = None
    size: Optional[int] = None


class PackageDetails(BaseModel):
    """Detailed information about a package from the registry."""

    identifier: str
    name: str
    publisher: str
    version: str  # Latest version
    summary: Optional[str] = None
    description: Optional[str] = None
    homepage: Optional[str] = None
    repository: Optional[str] = None
    license: Optional[str] = None
    # Stats
    downloads: Optional[int] = None
    downloads_this_week: Optional[int] = None
    downloads_this_month: Optional[int] = None
    # Versions
    versions: list[PackageVersion] = Field(default_factory=list)
    version_count: int = 0
    # Installation status
    installed: bool = False
    installed_version: Optional[str] = None
    installed_in: list[str] = Field(default_factory=list)


class PackageSummaryItem(BaseModel):
    """Display-ready package info for the packages panel.

    This is the unified type sent from /api/packages/summary that merges
    installed package data with registry metadata.
    """

    identifier: str
    name: str
    publisher: str

    # Installation status
    installed: bool
    version: Optional[str] = None  # Installed version
    installed_in: list[str] = Field(default_factory=list)

    # Registry info (pre-merged)
    latest_version: Optional[str] = None
    has_update: bool = False  # Pre-computed: version < latest_version

    # Display metadata
    summary: Optional[str] = None
    description: Optional[str] = None
    homepage: Optional[str] = None
    repository: Optional[str] = None
    license: Optional[str] = None

    # Stats
    downloads: Optional[int] = None
    version_count: Optional[int] = None
    keywords: list[str] = Field(default_factory=list)


class RegistryStatus(BaseModel):
    """Status of the registry connection for error visibility."""

    available: bool
    error: Optional[str] = None


class PackagesResponse(BaseModel):
    """Response for /api/packages endpoint."""

    packages: list[PackageInfo]
    total: int


class PackagesSummaryResponse(BaseModel):
    """Response for /api/packages/summary endpoint."""

    packages: list[PackageSummaryItem]
    total: int
    installed_count: int
    registry_status: RegistryStatus


class RegistrySearchResponse(BaseModel):
    """Response for /api/registry/search endpoint."""

    packages: list[PackageInfo]
    total: int
    query: str


class PackageActionRequest(BaseModel):
    """Request to install/update/remove a package."""

    package_identifier: str
    project_root: str
    version: Optional[str] = None  # If None, installs latest


class PackageActionResponse(BaseModel):
    """Response from package action."""

    success: bool
    message: str
    action: str  # 'install', 'update', 'remove'
