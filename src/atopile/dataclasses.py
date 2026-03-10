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
        serialize_by_alias=True,
    )


# =============================================================================
# File Explorer Models
# =============================================================================


class FileNode(CamelModel):
    """A node in the project file tree. Has children if folder, None if file."""

    name: str
    children: list["FileNode"] | None = None


# =============================================================================
# Build-related Pydantic Models
# =============================================================================


class BuildStage(CamelModel):
    """A stage within a build."""

    name: str
    stage_id: str = ""
    elapsed_seconds: float = 0.0
    status: StageStatus = StageStatus.PENDING
    infos: int = 0
    warnings: int = 0
    errors: int = 0


class Build(CamelModel):
    """A build (active, queued, or completed)."""

    # Core identification
    name: str
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
    entry: Optional[str] = None
    started_at: Optional[float] = None

    # Active build fields
    standalone: bool = False
    frozen: bool | None = False

    # Stages and logs
    stages: list[BuildStage] = Field(default_factory=list)
    # Total number of stages - set by subprocess at build start
    total_stages: Optional[int] = None

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
        values.setdefault("name", values.get("name") or "default")
        project_root = values.get("project_root")
        if project_root and not values.get("project_name"):
            values["project_name"] = Path(project_root).name
        return values


class BuildRequest(CamelModel):
    """Request to start a build."""

    project_root: str
    targets: list[str] = []  # Empty = all targets
    frozen: bool = False
    # For standalone builds (entry point without ato.yaml build config)
    entry: Optional[str] = None  # e.g., "main.ato:App" - if set, runs standalone build
    standalone: bool = False  # Whether to use standalone mode
    # Muster targets to include (e.g., "all", "mfg-data") - defaults to "default"
    include_targets: list[str] = []
    exclude_targets: list[str] = []


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


class ResolvedBuildTarget(CamelModel):
    """A build target with resolved artifact paths."""

    name: str
    entry: str = ""
    pcb_path: str
    model_path: str
    root: str


class Project(CamelModel):
    """A project discovered from ato.yaml."""

    root: str
    name: str
    targets: list[ResolvedBuildTarget]
    needs_migration: bool = False


class ProjectsResponse(CamelModel):
    """Response for /api/projects endpoint."""

    projects: list[Project]
    total: int


class ModuleChild(CamelModel):
    """A child field within a module (interface, parameter, nested module, etc.)."""

    name: str
    type_name: str  # The type name (e.g., "Electrical", "Resistor", "V")
    item_type: Literal["interface", "module", "component", "parameter", "trait"]
    children: list["ModuleChild"] = Field(default_factory=list)
    # For parameters: user-specified constraint (e.g., "50 kΩ ±10%", "0402")
    # None means no constraint was specified
    spec: Optional[str] = None


class ModuleDefinition(CamelModel):
    """A module/interface/component definition from an .ato file."""

    name: str
    type: Literal["module", "interface", "component"]
    file: str  # Relative path to the .ato file
    entry: str  # Entry point format: "file.ato:ModuleName"
    line: Optional[int] = None  # Line number where defined
    super_type: Optional[str] = None  # Parent type if extends
    children: list[ModuleChild] = Field(default_factory=list)  # Nested children


class ModulesResponse(CamelModel):
    """Response for /api/modules endpoint."""

    modules: list[ModuleDefinition]
    total: int


class DependencyInfo(CamelModel):
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


class DependenciesResponse(CamelModel):
    """Response for /api/dependencies endpoint."""

    dependencies: list[DependencyInfo]
    total: int


class CreateProjectRequest(BaseModel):
    parent_directory: str
    name: str | None = None


class CreateProjectResponse(CamelModel):
    success: bool
    message: str
    project_root: str | None = None
    project_name: str | None = None


class RenameProjectRequest(BaseModel):
    project_root: str
    new_name: str


class RenameProjectResponse(CamelModel):
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
    target: Optional[str] = None


class UpdateBuildTargetRequest(BaseModel):
    project_root: str
    old_name: str
    new_name: Optional[str] = None
    new_entry: Optional[str] = None


class UpdateBuildTargetResponse(BaseModel):
    success: bool
    message: str
    target: Optional[str] = None


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


class OpenLayoutRequest(CamelModel):
    project_root: str
    target: str


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
    has_update: bool = False
    # Stats from registry (may be None if not fetched)
    downloads: Optional[int] = None
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
    # Readme + build outputs
    readme: Optional[str] = None
    builds: Optional[list[str]] = None
    artifacts: list[PackageArtifact] = Field(default_factory=list)
    layouts: list[PackageLayout] = Field(default_factory=list)
    import_statements: list[PackageImportStatement] = Field(default_factory=list)
    # Installation status
    installed: bool = False
    installed_version: Optional[str] = None
    # Dependencies
    dependencies: list[PackageDependency] = Field(default_factory=list)


class PackageSummaryItem(CamelModel):
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
    keywords: list[str] = Field(default_factory=list)


class PackagesResponse(CamelModel):
    """Response for /api/packages endpoint."""

    packages: list[PackageInfo]
    total: int


class PackagesSummaryData(CamelModel):
    """Package summary data for the packages panel."""

    packages: list[PackageSummaryItem]
    total: int
    installed_count: int


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


class Problem(CamelModel):
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


class ProblemFilter(CamelModel):
    """Filter settings for problems."""

    levels: list[Literal["error", "warning"]] = Field(
        default_factory=lambda: ["error", "warning"]
    )
    build_names: list[str] = Field(default_factory=list)
    stage_ids: list[str] = Field(default_factory=list)


class ProblemsResponse(CamelModel):
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


class StdLibChild(CamelModel):
    """A child field within a standard library item."""

    name: str
    type: str  # The type name (e.g., "Electrical", "ElectricLogic")
    item_type: StdLibItemType  # Whether it's interface, parameter, etc.
    children: list["StdLibChild"] = Field(default_factory=list)
    enum_values: list[str] = Field(default_factory=list)


class StdLibItem(CamelModel):
    """A standard library item (module, interface, trait, etc.)."""

    id: str
    name: str
    type: StdLibItemType
    description: str
    usage: str | None = None
    children: list[StdLibChild] = Field(default_factory=list)
    parameters: list[dict[str, str]] = Field(default_factory=list)


class StdLibData(CamelModel):
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
# VS Code UI Store Models
# =============================================================================


class UiCoreStatus(CamelModel):
    """Core server status shared with the VS Code UI."""

    error: str | None = None
    uv_path: str = ""
    ato_binary: str = ""
    mode: Literal["local", "production"] = "production"
    version: str = ""
    core_server_port: int = 0


class UiExtensionSettings(CamelModel):
    """Extension settings mirrored into the backend store."""

    dev_path: str = ""
    auto_install: bool = True


class UiProjectState(CamelModel):
    """UI selection state for the active project/target/file."""

    selected_project: str | None = None
    selected_target: str | None = None
    active_file_path: str | None = None
    log_view_build_id: str | None = None
    log_view_stage: str | None = None


class UiPartSearchItem(CamelModel):
    """Display-ready part search result for the parts panel."""

    lcsc: str = ""
    mpn: str = ""
    manufacturer: str = ""
    description: str = ""
    stock: int = 0
    unit_cost: float | None = None
    datasheet_url: str | None = None
    package: str | None = None
    is_basic: bool = False
    is_preferred: bool = False
    attributes: dict[str, str] = Field(default_factory=dict)


class UiPartsSearchData(CamelModel):
    """Parts search state for the sidebar."""

    parts: list[UiPartSearchItem] = Field(default_factory=list)
    error: str | None = None


class UiInstalledPartItem(CamelModel):
    """Installed project part shown in the parts panel."""

    identifier: str = ""
    manufacturer: str = ""
    mpn: str = ""
    lcsc: str | None = None
    datasheet_url: str | None = None
    description: str = ""
    path: str = ""


class UiInstalledPartsData(CamelModel):
    """Installed parts state for the sidebar."""

    parts: list[UiInstalledPartItem] = Field(default_factory=list)


class UiPackageDetailState(CamelModel):
    """Selected package detail state for the shared detail view."""

    project_root: str | None = None
    package_id: str | None = None
    summary: PackageSummaryItem | None = None
    details: PackageDetails | None = None
    loading: bool = False
    error: str | None = None
    action_error: str | None = None


class UiPartDetail(CamelModel):
    """Expanded part detail shown in the shared detail view."""

    identifier: str = ""
    lcsc: str | None = None
    mpn: str = ""
    manufacturer: str = ""
    description: str = ""
    package: str | None = None
    datasheet_url: str | None = None
    path: str | None = None
    stock: int | None = None
    unit_cost: float | None = None
    is_basic: bool = False
    is_preferred: bool = False
    attributes: dict[str, str] = Field(default_factory=dict)
    footprint: str | None = None
    image_url: str | None = None
    import_statement: str | None = None
    installed: bool = False


class UiPartDetailState(CamelModel):
    """Selected part detail state for the shared detail view."""

    project_root: str | None = None
    lcsc: str | None = None
    part: UiPartDetail | None = None
    loading: bool = False
    error: str | None = None
    action_error: str | None = None


class UiMigrationStep(CamelModel):
    """Migration step metadata for the shared detail view."""

    id: str
    label: str
    description: str
    topic: str
    mandatory: bool = False
    order: int = 100


class UiMigrationTopic(CamelModel):
    """Migration topic metadata for the shared detail view."""

    id: str
    label: str
    icon: str


class UiMigrationStepResult(CamelModel):
    """Per-step execution state for a migration run."""

    step_id: str
    status: Literal["idle", "running", "success", "error"] = "idle"
    error: str | None = None


class UiMigrationState(CamelModel):
    """Selected migration detail state for the shared detail view."""

    project_root: str | None = None
    project_name: str | None = None
    needs_migration: bool = False
    steps: list[UiMigrationStep] = Field(default_factory=list)
    topics: list[UiMigrationTopic] = Field(default_factory=list)
    step_results: list[UiMigrationStepResult] = Field(default_factory=list)
    loading: bool = False
    running: bool = False
    completed: bool = False
    error: str | None = None


class UiSidebarDetails(CamelModel):
    """Shared detail surface state for package, part, and migration flows."""

    view: Literal["none", "package", "part", "migration"] = "none"
    package: UiPackageDetailState = Field(default_factory=UiPackageDetailState)
    part: UiPartDetailState = Field(default_factory=UiPartDetailState)
    migration: UiMigrationState = Field(default_factory=UiMigrationState)


class UiStructureData(CamelModel):
    """Structure panel data."""

    modules: list[ModuleDefinition] = Field(default_factory=list)
    total: int = 0


class UiVariable(CamelModel):
    """Simplified variable row used by the VS Code variables panel."""

    name: str = ""
    spec: str | None = None
    actual: str | None = None
    tolerance: str | None = None
    status: str | None = None


class UiVariableNode(CamelModel):
    """Simplified recursive variable node used by the VS Code variables panel."""

    name: str = ""
    variables: list[UiVariable] = Field(default_factory=list)
    children: list["UiVariableNode"] = Field(default_factory=list)


class UiVariablesData(CamelModel):
    """Variables panel data for the VS Code UI store."""

    nodes: list[UiVariableNode] = Field(default_factory=list)


class UiBOMParameter(CamelModel):
    """BOM parameter displayed in the VS Code UI."""

    name: str = ""
    value: str = ""
    unit: str | None = None


class UiBOMUsage(CamelModel):
    """BOM usage location displayed in the VS Code UI."""

    address: str = ""
    designator: str = ""
    line: int | None = None


class UiBOMComponent(CamelModel):
    """BOM component displayed in the VS Code UI."""

    id: str = ""
    lcsc: str | None = None
    mpn: str = ""
    manufacturer: str = ""
    type: str | None = None
    value: str = ""
    package: str = ""
    description: str = ""
    source: str | None = None
    stock: int | None = None
    unit_cost: float | None = None
    is_basic: bool | None = None
    is_preferred: bool | None = None
    quantity: int = 0
    parameters: list[UiBOMParameter] = Field(default_factory=list)
    usages: list[UiBOMUsage] = Field(default_factory=list)


class UiBOMData(CamelModel):
    """BOM panel data for the VS Code UI store."""

    version: str | None = None
    build_id: str | None = None
    components: list[UiBOMComponent] = Field(default_factory=list)
    total_quantity: int = 0
    unique_parts: int = 0
    estimated_cost: float | None = None
    out_of_stock: int = 0


class UiLogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    ALERT = "ALERT"


class UiAudience(StrEnum):
    USER = "user"
    DEVELOPER = "developer"
    AGENT = "agent"


class UiLogEntry(CamelModel):
    """Log entry as consumed by the VS Code logs panel."""

    id: int | None = None
    timestamp: str = ""
    level: UiLogLevel = UiLogLevel.INFO
    audience: UiAudience = UiAudience.USER
    logger_name: str = ""
    message: str = ""
    stage: str | None = None
    source_file: str | None = None
    source_line: int | None = None
    ato_traceback: str | None = None
    python_traceback: str | None = None
    objects: Any | None = None


class UiBuildLogRequest(CamelModel):
    """Request payload for the VS Code logs panel."""

    build_id: str = ""
    stage: str | None = None
    log_levels: list[UiLogLevel] | None = None
    audience: UiAudience | None = None
    count: int | None = None


class UiLogsStreamMessage(CamelModel):
    """Streamed log message for the VS Code logs panel."""

    type: Literal["logs_stream"] = "logs_stream"
    logs: list[UiLogEntry] = Field(default_factory=list)
    last_id: int = 0


class UiLogsErrorMessage(CamelModel):
    """Log stream error message for the VS Code logs panel."""

    type: Literal["logs_error"] = "logs_error"
    error: str


class UiSubscribeMessage(CamelModel):
    """Logical RPC subscribe message after transport/session routing."""

    type: Literal["subscribe"] = "subscribe"
    keys: list[str]


class UiStateMessage(CamelModel):
    """Logical RPC state message after transport/session routing."""

    type: Literal["state"] = "state"
    key: str
    data: Any


class UiActionMessage(CamelModel):
    """Logical RPC action message after transport/session routing."""

    model_config = ConfigDict(
        alias_generator=_to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        extra="allow",
    )

    type: Literal["action"] = "action"
    action: str


class UiActionResultMessage(CamelModel):
    """Logical RPC action result after transport/session routing."""

    model_config = ConfigDict(extra="allow")

    type: Literal["action_result"] = "action_result"
    request_id: str | None = None
    action: str
    ok: bool | None = None
    result: Any = None
    error: str | None = None


# =============================================================================
# atopile Configuration Pydantic Models
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
    """atopile configuration state."""

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
    # 'explicit-path', 'from-setting', or 'default'
    ato_source: Optional[str] = None
    # User's configured path (for explicit-path mode)
    ato_local_path: Optional[str] = None
    # Actual resolved binary path
    ato_binary_path: Optional[str] = None
    # Git branch when installed via uv from git
    ato_from_branch: Optional[str] = None
    # The pip/uv spec (for from-setting mode)
    ato_from_spec: Optional[str] = None


@dataclass(frozen=True)
class InstalledPackage:
    identifier: str
    version: str
    project_root: str


FileNode.model_rebuild()
ModuleChild.model_rebuild()
StdLibChild.model_rebuild()
UiVariableNode.model_rebuild()
