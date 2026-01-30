"""
Centralized data classes and Pydantic models for atopile.

This module serves as the single source of truth for all data structures
used throughout the atopile codebase, including:
- Pydantic BaseModel classes for API schemas
- Python dataclasses for internal data structures
- Type aliases and enums used in data models

Note: TypeScript types are generated from selected Pydantic models here via
`python scripts/generate_types.py`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, StrEnum
from pathlib import Path
from typing import Any, Literal, Optional, TypedDict

from fastapi import WebSocket
from pydantic import BaseModel, ConfigDict, Field, model_validator

# =============================================================================
# Enums and Type Aliases
# =============================================================================


class BuildStatus(str, Enum):
    """Build status states - overall status of a build."""

    QUEUED = "queued"
    BUILDING = "building"
    SUCCESS = "success"
    WARNING = "warning"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @classmethod
    def from_return_code(cls, return_code: int, warnings: int = 0) -> BuildStatus:
        """Derive terminal build status from a process return code."""
        if return_code != 0:
            return cls.FAILED
        return cls.WARNING if warnings > 0 else cls.SUCCESS


class StageStatus(str, Enum):
    """Stage status states - status of individual build stages."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    WARNING = "warning"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"


class EventType(StrEnum):
    """Event types emitted to WebSocket clients."""

    # Data state changes - client should refetch
    PROJECTS_CHANGED = "projects_changed"
    PACKAGES_CHANGED = "packages_changed"
    STDLIB_CHANGED = "stdlib_changed"
    BOM_CHANGED = "bom_changed"
    VARIABLES_CHANGED = "variables_changed"
    BUILDS_CHANGED = "builds_changed"
    PROBLEMS_CHANGED = "problems_changed"

    # File watcher notifications
    PROJECT_FILES_CHANGED = "project_files_changed"
    PROJECT_MODULES_CHANGED = "project_modules_changed"
    PROJECT_DEPENDENCIES_CHANGED = "project_dependencies_changed"

    # Configuration changes
    ATOPILE_CONFIG_CHANGED = "atopile_config_changed"

    # Shared UI state
    LOG_VIEW_CURRENT_ID_CHANGED = "log_view_current_id_changed"

    # Action requests (frontend should handle)
    OPEN_LAYOUT = "open_layout"
    OPEN_KICAD = "open_kicad"
    OPEN_3D = "open_3d"


# =============================================================================
# Build-related Dataclasses (from logging.py)
# =============================================================================


@dataclass
class ProjectState:
    """Aggregate state for a project containing multiple builds."""

    builds: list = field(default_factory=list)
    status: BuildStatus = BuildStatus.QUEUED
    completed: int = 0
    failed: int = 0
    warnings: int = 0
    building: int = 0
    queued: int = 0
    total: int = 0
    current_build: str | None = None
    current_stage: str | None = None
    elapsed: float = 0.0


@dataclass(frozen=True)
class StageCompleteEvent:
    duration: float
    status: StageStatus  # Use StageStatus enum instead of plain string
    infos: int
    warnings: int
    errors: int
    alerts: int
    log_name: str
    description: str


# =============================================================================
# Logging DB Models
# =============================================================================


@dataclass
class BuildRow:
    """Database model for build metadata in logs database."""

    build_id: str
    project_path: str
    target: str
    timestamp: str
    created_at: str = ""


@dataclass
class LogRow:
    """Database model for log entries."""

    id: int | None = field(default=None, init=False)
    build_id: str = ""
    timestamp: str = ""
    stage: str = ""
    level: str = ""
    message: str = ""
    logger_name: str = ""
    audience: str = "developer"
    source_file: str | None = None
    source_line: int | None = None
    ato_traceback: str | None = None
    python_traceback: str | None = None
    objects: str | None = None


@dataclass
class TestRunRow:
    """Database model for test run metadata."""

    test_run_id: str
    created_at: str = ""


@dataclass
class TestLogRow:
    """Database model for test log entries."""

    id: int | None = field(default=None, init=False)
    test_run_id: str = ""
    timestamp: str = ""
    test_name: str = ""
    level: str = ""
    message: str = ""
    logger_name: str = ""
    audience: str = "developer"
    source_file: str | None = None
    source_line: int | None = None
    ato_traceback: str | None = None
    python_traceback: str | None = None
    objects: str | None = None


# =============================================================================
# Log-related Data Structures
# =============================================================================


class LocalVar(TypedDict, total=False):
    """A serialized local variable from a stack frame."""

    type: str  # e.g., "int", "str", "Parameter"
    repr: str  # Truncated repr() representation
    value: Any  # JSON-native value if serializable (optional)


class StackFrame(TypedDict):
    """A single stack frame from a structured traceback."""

    filename: str
    lineno: int
    function: str
    code_line: str | None  # Source line if available
    locals: dict[str, LocalVar]


class StructuredTraceback(TypedDict):
    """
    Structured traceback with stack frames and local variables.

    Used for IDE-like stack inspector UI where users can expand frames
    and inspect variables.
    """

    exc_type: str  # e.g., "AssertionError"
    exc_message: str  # e.g., "Parameter not constrained"
    frames: list[StackFrame]  # Bottom-up (most recent last)


class Log:
    """Namespace for all log-related data structures."""

    class Audience(StrEnum):
        """Who a log message is intended for."""

        USER = "user"
        DEVELOPER = "developer"
        AGENT = "agent"

    class Level(StrEnum):
        """Log levels."""

        DEBUG = "DEBUG"
        INFO = "INFO"
        WARNING = "WARNING"
        ERROR = "ERROR"
        ALERT = "ALERT"

    # -------------------------------------------------------------------------
    # Base dataclasses for log entries
    # -------------------------------------------------------------------------

    @dataclass
    class _BaseEntry:
        """Base dataclass with shared required fields for all log entries."""

        timestamp: str
        level: Log.Level
        logger_name: str
        message: str

    @dataclass
    class Entry(_BaseEntry):
        """A structured build log entry."""

        build_id: str
        stage: str
        audience: Log.Audience | None = field(
            default=None
        )  # Set to Log.Audience.DEVELOPER after class definition
        source_file: str | None = None
        source_line: int | None = None
        ato_traceback: str | None = None
        python_traceback: str | None = None
        objects: dict | None = None

    @dataclass
    class TestEntry(_BaseEntry):
        """A structured test log entry."""

        test_run_id: str
        test_name: str  # Name of the Python test being run
        audience: Log.Audience | None = field(
            default=None
        )  # Set to Log.Audience.DEVELOPER after class definition
        source_file: str | None = None
        source_line: int | None = None
        ato_traceback: str | None = None
        python_traceback: str | None = None
        objects: dict | None = None

    # -------------------------------------------------------------------------
    # Base Pydantic models for log entry queries
    # -------------------------------------------------------------------------

    class _BaseQuery(BaseModel):
        """Base query parameters with shared fields."""

        log_levels: list[Log.Level] | None = None
        audience: Log.Audience | None = None
        count: int = Field(default=500, ge=1)

    class BuildQuery(_BaseQuery):
        """Query parameters for fetching build logs."""

        build_id: str
        stage: str | None = None

    class TestQuery(_BaseQuery):
        """Query parameters for fetching test logs."""

        test_run_id: str
        test_name: str | None = None

    # -------------------------------------------------------------------------
    # Base Pydantic models for log entry serialization
    # -------------------------------------------------------------------------

    class _BaseEntryPydantic(BaseModel):
        """Base Pydantic model with shared fields for log entry serialization."""

        timestamp: str
        level: str
        audience: str
        logger_name: str
        message: str
        source_file: str | None = None
        source_line: int | None = None
        ato_traceback: str | None = None
        python_traceback: str | None = None
        objects: Any | None = None

    class BuildEntryPydantic(_BaseEntryPydantic):
        """Pydantic model for build log entry (API serialization)."""

        stage: str | None = None

    class TestEntryPydantic(_BaseEntryPydantic):
        """Pydantic model for test log entry (API serialization)."""

        test_name: str | None = None

    # -------------------------------------------------------------------------
    # Pydantic models for log entry results
    # -------------------------------------------------------------------------

    class BuildResult(BaseModel):
        """Response containing build log entries."""

        type: Literal["logs_result"] = "logs_result"
        logs: list["Log.BuildEntryPydantic"]

    class TestResult(BaseModel):
        """Response containing test log entries."""

        type: Literal["test_logs_result"] = "test_logs_result"
        logs: list["Log.TestEntryPydantic"]

    class Error(BaseModel):
        """Error response for log queries."""

        type: Literal["logs_error"] = "logs_error"
        error: str

    # -------------------------------------------------------------------------
    # Streaming models (for real-time log updates)
    # -------------------------------------------------------------------------

    class _BaseStreamQuery(_BaseQuery):
        """Base streaming query parameters with shared fields."""

        after_id: int = 0  # Cursor - only return logs with id > after_id
        count: int = Field(default=1000, ge=1, le=5000)

    class BuildStreamQuery(_BaseStreamQuery):
        """Query parameters for streaming build logs."""

        build_id: str
        stage: str | None = None

    class TestStreamQuery(_BaseStreamQuery):
        """Query parameters for streaming test logs."""

        test_run_id: str
        test_name: str | None = None

    class _BaseStreamEntryPydantic(_BaseEntryPydantic):
        """Base streaming log entry with id for cursor tracking."""

        id: int  # Database row id for cursor

    class BuildStreamEntryPydantic(_BaseStreamEntryPydantic):
        """Build log entry with id for streaming (cursor tracking)."""

        stage: str | None = None

    class TestStreamEntryPydantic(_BaseStreamEntryPydantic):
        """Test log entry with id for streaming."""

        test_name: str | None = None

    class BuildStreamResult(BaseModel):
        """Streaming response with cursor."""

        type: Literal["logs_stream"] = "logs_stream"
        logs: list["Log.BuildStreamEntryPydantic"]
        last_id: int  # Highest id returned - client sends this back as after_id

    class TestStreamResult(BaseModel):
        """Streaming response for test logs."""

        type: Literal["test_logs_stream"] = "test_logs_stream"
        logs: list["Log.TestStreamEntryPydantic"]
        last_id: int


# Set default values for dataclass fields after Log class is fully defined
# (Can't reference Log.Audience.DEVELOPER in field default during class definition)
Log.Entry.__dataclass_fields__["audience"].default = Log.Audience.DEVELOPER
Log.TestEntry.__dataclass_fields__["audience"].default = Log.Audience.DEVELOPER


def _to_camel(s: str) -> str:
    """Convert snake_case to camelCase."""
    components = s.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=_to_camel,
        populate_by_name=True,
    )


# =============================================================================
# Build-related Pydantic Models
# =============================================================================


class BuildStage(CamelModel):
    """A stage within a build."""

    name: str
    stage_id: str = ""
    display_name: Optional[str] = None
    elapsed_seconds: float = 0.0
    status: StageStatus = StageStatus.PENDING
    infos: int = 0
    warnings: int = 0
    errors: int = 0
    alerts: int = 0


class Build(CamelModel):
    """A build (active, queued, or completed)."""

    # Core identification
    name: str
    display_name: str
    project_name: Optional[str] = None
    build_id: Optional[str] = None

    # Status
    status: BuildStatus = BuildStatus.QUEUED
    elapsed_seconds: float = 0.0
    warnings: int = 0
    errors: int = 0
    return_code: Optional[int] = None
    error: Optional[str] = None  # Error message from build failure

    # Context
    project_root: Optional[str] = None
    target: Optional[str] = None
    entry: Optional[str] = None
    started_at: Optional[float] = None

    # Active build fields
    timestamp: Optional[str] = None
    standalone: bool = False
    frozen: bool | None = False

    # Stages and logs
    stages: list[dict[str, Any]] = Field(default_factory=list)
    # Total number of stages - set by subprocess at build start
    total_stages: Optional[int] = None
    log_dir: Optional[str] = None
    log_file: Optional[str] = None

    # Queue info
    queue_position: Optional[int] = None

    # Build options (used to construct subprocess command/env, not serialized)
    include_targets: list[str] = Field(default_factory=list, exclude=True)
    exclude_targets: list[str] = Field(default_factory=list, exclude=True)
    keep_picked_parts: bool | None = Field(default=None, exclude=True)
    keep_net_names: bool | None = Field(default=None, exclude=True)
    keep_designators: bool | None = Field(default=None, exclude=True)
    verbose: bool = Field(default=False, exclude=True)

    @model_validator(mode="before")
    @classmethod
    def _fill_display_fields(cls, values: Any) -> Any:
        if not isinstance(values, dict):
            return values
        target = values.get("target") or values.get("name") or "default"
        values.setdefault("name", target)
        project_root = values.get("project_root")
        if project_root and not values.get("project_name"):
            values["project_name"] = Path(project_root).name
        if not values.get("display_name"):
            if values.get("project_name"):
                values["display_name"] = f"{values['project_name']}:{values['name']}"
            else:
                values["display_name"] = values["name"]
        return values


class BuildRequest(CamelModel):
    """Request to start a build."""

    project_root: str
    targets: list[str] = []  # Empty = all targets
    frozen: bool = False
    # For standalone builds (entry point without ato.yaml build config)
    entry: Optional[str] = None  # e.g., "main.ato:App" - if set, runs standalone build
    standalone: bool = False  # Whether to use standalone mode


class BuildTargetInfo(CamelModel):
    """Build target queued by a build request."""

    target: str
    build_id: str


class BuildResponse(CamelModel):
    """Response from build request."""

    success: bool
    message: str
    build_targets: list[BuildTargetInfo] = Field(default_factory=list)


class BuildTargetResponse(CamelModel):
    """Response for build target status (one build_id = one target)."""

    build_id: str
    target: str
    status: BuildStatus
    project_root: str
    return_code: Optional[int] = None
    error: Optional[str] = None


class BuildTargetStatus(CamelModel):
    """Persisted status from last build of a target."""

    status: BuildStatus
    timestamp: str  # ISO format
    elapsed_seconds: Optional[float] = None
    warnings: int = 0
    errors: int = 0
    stages: Optional[list[dict]] = None
    build_id: Optional[str] = None  # Build ID hash for reference


class EventMessage(BaseModel):
    """WebSocket event message payload."""

    type: Literal["event"] = "event"
    event: EventType
    data: Optional[dict[str, Any]] = None


class BuildTarget(CamelModel):
    """A build target from ato.yaml."""

    name: str
    entry: str
    root: str
    last_build: Optional[BuildTargetStatus] = None


class BuildsResponse(CamelModel):
    """Response for /api/builds endpoints."""

    builds: list[Build]
    total: Optional[int] = None


class MaxConcurrentRequest(BaseModel):
    use_default: bool = True
    custom_value: int | None = None


# =============================================================================
# Project-related Pydantic Models
# =============================================================================


class Project(CamelModel):
    """A project discovered from ato.yaml."""

    root: str
    name: str
    targets: list[BuildTarget]
    display_path: Optional[str] = (
        None  # Relative path for display (e.g., "packages/proj")
    )


class ProjectsResponse(CamelModel):
    """Response for /api/projects endpoint."""

    projects: list[Project]
    total: int


class ModuleChild(BaseModel):
    """A child field within a module (interface, parameter, nested module, etc.)."""

    model_config = ConfigDict(
        alias_generator=_to_camel,
        populate_by_name=True,
    )

    name: str
    type_name: str  # The type name (e.g., "Electrical", "Resistor", "V")
    item_type: Literal["interface", "module", "component", "parameter", "trait"]
    children: list["ModuleChild"] = Field(default_factory=list)
    # For parameters: user-specified constraint (e.g., "50 kΩ ±10%", "0402")
    # None means no constraint was specified
    spec: Optional[str] = None


class ModuleDefinition(BaseModel):
    """A module/interface/component definition from an .ato file."""

    name: str
    type: Literal["module", "interface", "component"]
    file: str  # Relative path to the .ato file
    entry: str  # Entry point format: "file.ato:ModuleName"
    line: Optional[int] = None  # Line number where defined
    super_type: Optional[str] = None  # Parent type if extends
    children: list[ModuleChild] = Field(default_factory=list)  # Nested children


class ModulesResponse(BaseModel):
    """Response for /api/modules endpoint."""

    modules: list[ModuleDefinition]
    total: int


class DependencyInfo(BaseModel):
    """A project dependency with version info."""

    identifier: str  # e.g., "atopile/resistors"
    version: str  # Installed version
    latest_version: Optional[str] = None  # Latest available version
    name: str  # e.g., "resistors"
    publisher: str  # e.g., "atopile"
    repository: Optional[str] = None
    has_update: bool = False
    is_direct: bool = False
    via: Optional[list[str]] = None
    status: Optional[str] = None


class DependenciesResponse(BaseModel):
    """Response for /api/dependencies endpoint."""

    dependencies: list[DependencyInfo]
    total: int


class CreateProjectRequest(BaseModel):
    parent_directory: str
    name: str | None = None


class CreateProjectResponse(BaseModel):
    success: bool
    message: str
    project_root: str | None = None
    project_name: str | None = None


class RenameProjectRequest(BaseModel):
    project_root: str
    new_name: str


class RenameProjectResponse(BaseModel):
    success: bool
    message: str
    old_root: str
    new_root: str | None = None


# --- Build Target Management ---


class AddBuildTargetRequest(BaseModel):
    project_root: str
    name: str
    entry: str


class AddBuildTargetResponse(BaseModel):
    success: bool
    message: str
    target: Optional[dict] = None


class UpdateBuildTargetRequest(BaseModel):
    project_root: str
    old_name: str
    new_name: Optional[str] = None
    new_entry: Optional[str] = None


class UpdateBuildTargetResponse(BaseModel):
    success: bool
    message: str
    target: Optional[dict] = None


class DeleteBuildTargetRequest(BaseModel):
    project_root: str
    name: str


class DeleteBuildTargetResponse(BaseModel):
    success: bool
    message: str


# --- Dependency Management ---


class UpdateDependencyVersionRequest(BaseModel):
    project_root: str
    identifier: str
    new_version: str


class UpdateDependencyVersionResponse(BaseModel):
    success: bool
    message: str


# =============================================================================
# Package-related Pydantic Models
# =============================================================================


class PackageInfo(CamelModel):
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


class PackageVersion(CamelModel):
    """Information about a package version/release."""

    version: str
    released_at: Optional[str] = None
    requires_atopile: Optional[str] = None
    size: Optional[int] = None


class PackageDependency(CamelModel):
    """A package dependency."""

    identifier: str
    version: Optional[str] = None  # Required version/release


class PackageFileHashes(CamelModel):
    sha256: str


class PackageAuthor(CamelModel):
    name: str
    email: Optional[str] = None


class PackageArtifact(CamelModel):
    filename: str
    url: str
    size: int
    hashes: PackageFileHashes
    build_name: Optional[str] = None


class PackageLayout(CamelModel):
    build_name: str
    url: str


class PackageImportStatement(CamelModel):
    build_name: str
    import_statement: str


class PackageDetails(CamelModel):
    """Detailed information about a package from the registry."""

    identifier: str
    name: str
    publisher: str
    version: str  # Latest version
    created_at: Optional[str] = None
    released_at: Optional[str] = None
    authors: list[PackageAuthor] = Field(default_factory=list)
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
    # Readme + build outputs
    readme: Optional[str] = None
    builds: Optional[list[str]] = None
    artifacts: list[PackageArtifact] = Field(default_factory=list)
    layouts: list[PackageLayout] = Field(default_factory=list)
    import_statements: list[PackageImportStatement] = Field(default_factory=list)
    # Installation status
    installed: bool = False
    installed_version: Optional[str] = None
    installed_in: list[str] = Field(default_factory=list)
    # Dependencies
    dependencies: list[PackageDependency] = Field(default_factory=list)


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


class RegistryStatus(CamelModel):
    """Status of the registry connection for error visibility."""

    available: bool
    error: Optional[str] = None


class PackagesResponse(CamelModel):
    """Response for /api/packages endpoint."""

    packages: list[PackageInfo]
    total: int


class PackagesSummaryResponse(CamelModel):
    """Response for /api/packages/summary endpoint."""

    packages: list[PackageSummaryItem]
    total: int
    installed_count: int
    registry_status: RegistryStatus


class RegistrySearchResponse(CamelModel):
    """Response for /api/registry/search endpoint."""

    packages: list[PackageInfo]
    total: int
    query: str


class PackageActionRequest(CamelModel):
    """Request to install/update/remove a package."""

    package_identifier: str
    project_root: str
    version: Optional[str] = None  # If None, installs latest


class PackageActionResponse(CamelModel):
    """Response from package action."""

    success: bool
    message: str
    action: str  # 'install', 'update', 'remove'


class SyncPackagesRequest(CamelModel):
    """Request to sync packages for a project."""

    project_root: str
    force: bool = False  # If True, overwrite locally modified packages


class SyncPackagesResponse(CamelModel):
    """Response from sync packages action."""

    success: bool
    message: str
    operation_id: Optional[str] = None  # For tracking async operation status
    modified_packages: Optional[list[str]] = None  # Packages that were modified


class PackageInfoVeryBrief(CamelModel):
    identifier: str
    version: str
    summary: str


# =============================================================================
# Problem-related Pydantic Models
# =============================================================================


class Problem(BaseModel):
    """A problem (error or warning) from a build log."""

    id: str
    level: Literal["error", "warning"]
    message: str
    file: Optional[str] = None
    line: Optional[int] = None
    column: Optional[int] = None
    stage: Optional[str] = None
    logger: Optional[str] = None
    build_name: Optional[str] = None
    project_name: Optional[str] = None
    timestamp: Optional[str] = None
    ato_traceback: Optional[str] = None
    exc_info: Optional[str] = None


class ProblemFilter(BaseModel):
    """Filter settings for problems."""

    levels: list[Literal["error", "warning"]] = Field(
        default_factory=lambda: ["error", "warning"]
    )
    build_names: list[str] = Field(default_factory=list)
    stage_ids: list[str] = Field(default_factory=list)


class ProblemsResponse(BaseModel):
    """Response for /api/problems endpoint."""

    problems: list[Problem]
    total: int
    error_count: int
    warning_count: int


# Log-related models are now in the Log class above


# =============================================================================
# Standard Library Pydantic Models
# =============================================================================


class StdLibItemType(str, Enum):
    """Type of standard library item."""

    INTERFACE = "interface"
    MODULE = "module"
    COMPONENT = "component"
    TRAIT = "trait"
    PARAMETER = "parameter"


class StdLibChild(BaseModel):
    """A child field within a standard library item."""

    name: str
    type: str  # The type name (e.g., "Electrical", "ElectricLogic")
    item_type: StdLibItemType  # Whether it's interface, parameter, etc.
    children: list["StdLibChild"] = Field(default_factory=list)
    enum_values: list[str] = Field(default_factory=list)


class StdLibItem(BaseModel):
    """A standard library item (module, interface, trait, etc.)."""

    id: str
    name: str
    type: StdLibItemType
    description: str
    usage: str | None = None
    children: list[StdLibChild] = Field(default_factory=list)
    parameters: list[dict[str, str]] = Field(default_factory=list)


class StdLibResponse(BaseModel):
    """Response for /api/stdlib endpoint."""

    items: list[StdLibItem]
    total: int


# =============================================================================
# BOM-related Pydantic Models
# =============================================================================


class BOMParameter(BaseModel):
    """BOM component parameter."""

    name: str
    value: str
    unit: Optional[str] = None


class BOMUsage(BaseModel):
    """BOM component usage location."""

    address: str
    designator: str


class BOMComponent(BaseModel):
    """BOM component."""

    id: str
    lcsc: Optional[str] = None
    manufacturer: Optional[str] = None
    mpn: Optional[str] = None
    type: str
    value: str
    package: str
    description: Optional[str] = None
    quantity: int = 1
    unit_cost: Optional[float] = None
    stock: Optional[int] = None
    is_basic: Optional[bool] = None
    is_preferred: Optional[bool] = None
    source: str = "picked"
    parameters: list[BOMParameter] = Field(default_factory=list)
    usages: list[BOMUsage] = Field(default_factory=list)


class BOMData(BaseModel):
    """Bill of Materials data."""

    version: str = "1.0"
    components: list[BOMComponent] = Field(default_factory=list)


# =============================================================================
# Variables-related Pydantic Models
# =============================================================================


class Variable(BaseModel):
    """A variable in the design."""

    name: str
    spec: Optional[str] = None
    spec_tolerance: Optional[str] = None
    actual: Optional[str] = None
    actual_tolerance: Optional[str] = None
    unit: Optional[str] = None
    type: str = "dimensionless"
    meets_spec: Optional[bool] = None
    source: Optional[str] = None


class VariableNode(BaseModel):
    """A node in the variable tree."""

    name: str
    type: Literal["module", "interface", "component"]
    path: str
    type_name: Optional[str] = None
    variables: Optional[list[Variable]] = None
    children: Optional[list["VariableNode"]] = None


class VariablesData(BaseModel):
    """Variables data for a build target."""

    version: str = "1.0"
    nodes: list[VariableNode] = Field(default_factory=list)


# =============================================================================
# Atopile Configuration Pydantic Models
# =============================================================================


class DetectedInstallation(BaseModel):
    """A detected atopile installation."""

    path: str
    version: Optional[str] = None
    source: Literal["path", "venv", "manual"] = "path"


class InstallProgress(BaseModel):
    """Installation progress info."""

    message: str
    percent: Optional[float] = None


class AtopileConfig(BaseModel):
    """Atopile configuration state."""

    current_version: str = ""
    source: Literal["release", "branch", "local"] = "release"
    local_path: Optional[str] = None
    branch: Optional[str] = None
    available_versions: list[str] = Field(default_factory=list)
    available_branches: list[str] = Field(default_factory=list)
    detected_installations: list[DetectedInstallation] = Field(default_factory=list)
    is_installing: bool = False
    install_progress: Optional[InstallProgress] = None
    error: Optional[str] = None


# =============================================================================
# WebSocket State Manager Dataclass
# =============================================================================


@dataclass
class ConnectedClient:
    """A connected WebSocket client."""

    client_id: str
    websocket: WebSocket
    subscribed: bool = True  # Whether to receive state updates


# =============================================================================
# MCP-related Pydantic Models
# =============================================================================


class Language(StrEnum):
    FABLL = "fabll(python)"
    ATO = "ato"


class NodeType(StrEnum):
    MODULE = "Module"
    INTERFACE = "Interface"


class NodeInfo(BaseModel):
    name: str
    docstring: str
    locator: str
    language: Language
    code: str


class NodeInfoOverview(BaseModel):
    name: str
    docstring: str
    language: Language
    type: NodeType


class Result(BaseModel):
    success: bool
    project_dir: str


class ErrorResult(Result):
    error: str
    error_message: str


class BuildResult(Result):
    target: str
    logs: str


class PackageVerifyResult(Result):
    logs: str


class CreatePartResult(Result):
    manufacturer: str
    part_number: str
    description: str
    supplier_id: str
    stock: int
    path: str
    import_statement: str


class CreatePartError(ErrorResult):
    error: str
    error_message: str


class InstallPackageResult(Result):
    installed_packages: list[str]


class InstallPackageError(ErrorResult):
    pass


# =============================================================================
# Build Steps Dataclasses
# =============================================================================


@dataclass
class BuildReport:
    name: str
    status: BuildStatus  # Use BuildStatus enum instead of Status
    warnings: int
    errors: int
    stages: list[StageCompleteEvent]


# =============================================================================
# Server Context Dataclasses
# =============================================================================


@dataclass
class AppContext:
    summary_file: Optional[Path] = None
    workspace_paths: list[Path] = field(default_factory=list)
    ato_source: Optional[str] = None
    ato_ui_source: Optional[str] = None
    ato_local_path: Optional[str] = None
    ato_binary_path: Optional[str] = None  # Actual resolved binary path

    @property
    def workspace_path(self) -> Optional[Path]:
        """Return the first workspace path, or None if no workspaces."""
        return self.workspace_paths[0] if self.workspace_paths else None

    @workspace_path.setter
    def workspace_path(self, value: Optional[Path]) -> None:
        """Set the first workspace path."""
        if value is None:
            self.workspace_paths = []
        elif self.workspace_paths:
            self.workspace_paths[0] = value
        else:
            self.workspace_paths = [value]


@dataclass(frozen=True)
class InstalledPackage:
    identifier: str
    version: str
    project_root: str
