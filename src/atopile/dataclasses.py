"""
Centralized data classes and Pydantic models for atopile.

This module serves as the single source of truth for all data structures
used throughout the atopile codebase, including:
- Pydantic BaseModel classes for API schemas
- Python dataclasses for internal data structures
- Type aliases and enums used in data models
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, StrEnum
from pathlib import Path
from typing import Any, Literal, Optional

from fastapi import WebSocket
from pydantic import BaseModel, ConfigDict, Field

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
class StageStatusEvent:
    name: str
    description: str
    progress: int
    total: int | None


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
# Log-related Data Structures
# =============================================================================


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
        logs: list["BuildEntryPydantic"]

    class TestResult(BaseModel):
        """Response containing test log entries."""

        type: Literal["test_logs_result"] = "test_logs_result"
        logs: list["TestEntryPydantic"]

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
        logs: list["BuildStreamEntryPydantic"]
        last_id: int  # Highest id returned - client sends this back as after_id

    class TestStreamResult(BaseModel):
        """Streaming response for test logs."""

        type: Literal["test_logs_stream"] = "test_logs_stream"
        logs: list["TestStreamEntryPydantic"]
        last_id: int


# Set default values for dataclass fields after Log class is fully defined
# (Can't reference Log.Audience.DEVELOPER in field default during class definition)
Log.Entry.__dataclass_fields__["audience"].default = Log.Audience.DEVELOPER
Log.TestEntry.__dataclass_fields__["audience"].default = Log.Audience.DEVELOPER


# =============================================================================
# Build-related Pydantic Models
# =============================================================================


class BuildStage(BaseModel):
    """A stage within a build."""

    name: str
    stage_id: str
    display_name: Optional[str] = None
    elapsed_seconds: float = 0.0
    status: StageStatus = StageStatus.PENDING
    infos: int = 0
    warnings: int = 0
    errors: int = 0
    alerts: int = 0


class Build(BaseModel):
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
    targets: Optional[list[str]] = None
    entry: Optional[str] = None
    started_at: Optional[float] = None

    # Stages and logs
    stages: Optional[list[BuildStage]] = None
    # TODO: Replace this estimate once builds are defined in the graph
    # This is the expected total number of stages for progress calculation
    total_stages: int = 20  # Estimated total stages for progress bar
    log_dir: Optional[str] = None
    log_file: Optional[str] = None

    # Queue info
    queue_position: Optional[int] = None


class BuildRequest(BaseModel):
    """Request to start a build."""

    project_root: str
    targets: list[str] = []  # Empty = all targets
    frozen: bool = False
    # For standalone builds (entry point without ato.yaml build config)
    entry: Optional[str] = None  # e.g., "main.ato:App" - if set, runs standalone build
    standalone: bool = False  # Whether to use standalone mode


class BuildTargetInfo(BaseModel):
    """Build target queued by a build request."""

    target: str
    build_id: str


class BuildResponse(BaseModel):
    """Response from build request."""

    success: bool
    message: str
    build_id: Optional[str] = None
    targets: list[str] = Field(default_factory=list)
    build_targets: list[BuildTargetInfo] = Field(default_factory=list)


class BuildStatusResponse(BaseModel):
    """Response for build status."""

    build_id: str
    status: BuildStatus  # Use BuildStatus enum
    project_root: str
    targets: list[str]
    return_code: Optional[int] = None
    error: Optional[str] = None


class BuildTargetStatus(BaseModel):
    """Persisted status from last build of a target."""

    status: BuildStatus
    timestamp: str  # ISO format
    elapsed_seconds: Optional[float] = None
    warnings: int = 0
    errors: int = 0
    stages: Optional[list[dict]] = None


class BuildTarget(BaseModel):
    """A build target from ato.yaml."""

    name: str
    entry: str
    root: str
    last_build: Optional[BuildTargetStatus] = None


class MaxConcurrentRequest(BaseModel):
    use_default: bool = True
    custom_value: int | None = None


# =============================================================================
# Project-related Pydantic Models
# =============================================================================


class Project(BaseModel):
    """A project discovered from ato.yaml."""

    root: str
    name: str
    targets: list[BuildTarget]


class ProjectsResponse(BaseModel):
    """Response for /api/projects endpoint."""

    projects: list[Project]
    total: int


def _to_camel(s: str) -> str:
    """Convert snake_case to camelCase."""
    components = s.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


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


class FileTreeNode(BaseModel):
    """A node in the file tree (either a file or folder)."""

    name: str
    path: str
    type: Literal["file", "folder"]
    extension: Optional[str] = None  # 'ato' or 'py' for files
    children: Optional[list["FileTreeNode"]] = None


class FilesResponse(BaseModel):
    """Response for /api/files endpoint."""

    files: list[FileTreeNode]
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


class PackageDependency(BaseModel):
    """A package dependency."""

    identifier: str
    version: Optional[str] = None  # Required version/release


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


class PackageInfoVeryBrief(BaseModel):
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
# AppState Pydantic Model
# =============================================================================


class AppState(BaseModel):
    """
    THE SINGLE APP STATE - All state lives here.

    Python server owns this state and pushes it to all connected clients
    via WebSocket on every change.
    """

    # Connection
    is_connected: bool = True

    # Projects (from ato.yaml)
    projects: list[Project] = Field(default_factory=list)
    is_loading_projects: bool = False
    projects_error: Optional[str] = None
    selected_project_root: Optional[str] = None
    selected_target_names: list[str] = Field(default_factory=list)

    # Builds (completed builds from /api/summary)
    builds: list[Build] = Field(default_factory=list)

    # Queued builds (from /api/builds/active)
    queued_builds: list[Build] = Field(default_factory=list)

    # Packages
    packages: list[PackageInfo] = Field(default_factory=list)
    is_loading_packages: bool = False
    packages_error: Optional[str] = None

    # Standard Library
    stdlib_items: list[StdLibItem] = Field(default_factory=list)
    is_loading_stdlib: bool = False

    # BOM
    bom_data: Optional[BOMData] = None
    is_loading_bom: bool = False
    bom_error: Optional[str] = None

    # Package details
    selected_package_details: Optional[PackageDetails] = None
    is_loading_package_details: bool = False
    package_details_error: Optional[str] = None

    # Build selection
    selected_build_name: Optional[str] = None
    selected_project_name: Optional[str] = None

    # Sidebar UI
    expanded_targets: list[str] = Field(default_factory=list)

    # Extension info
    version: str = "dev"
    logo_uri: str = ""

    # Atopile configuration
    atopile: AtopileConfig = Field(default_factory=AtopileConfig)

    # Problems
    problems: list[Problem] = Field(default_factory=list)
    is_loading_problems: bool = False
    problem_filter: ProblemFilter = Field(default_factory=ProblemFilter)

    # Developer mode - shows all log audiences instead of just 'user'
    developer_mode: bool = False

    # Project modules
    project_modules: dict[str, list[ModuleDefinition]] = Field(default_factory=dict)
    is_loading_modules: bool = False

    # Project files
    project_files: dict[str, list[FileTreeNode]] = Field(default_factory=dict)
    is_loading_files: bool = False

    # Project dependencies
    project_dependencies: dict[str, list[DependencyInfo]] = Field(default_factory=dict)
    is_loading_dependencies: bool = False

    # Variables
    current_variables_data: Optional[VariablesData] = None
    is_loading_variables: bool = False
    variables_error: Optional[str] = None

    # Open signals (one-shot signals to open files/apps)
    open_file: Optional[str] = None
    open_file_line: Optional[int] = None
    open_file_column: Optional[int] = None
    open_layout: Optional[str] = None
    open_kicad: Optional[str] = None
    open_3d: Optional[str] = None

    class Config:
        # Use camelCase for JSON serialization to match frontend
        populate_by_name = True

    def to_frontend_dict(self) -> dict:
        """Convert to dict with camelCase keys for frontend compatibility."""
        # Get the dict representation
        data = self.model_dump()

        # Convert snake_case to camelCase
        def to_camel(s: str) -> str:
            components = s.split("_")
            return components[0] + "".join(x.title() for x in components[1:])

        def is_path_key(k: str) -> bool:
            """Check if a key looks like a file path (should not be converted)."""
            return "/" in k or k.startswith(".")

        def convert_keys(obj: Any) -> Any:
            if isinstance(obj, dict):
                return {
                    (k if is_path_key(k) else to_camel(k)): convert_keys(v)
                    for k, v in obj.items()
                }
            elif isinstance(obj, list):
                return [convert_keys(item) for item in obj]
            else:
                return obj

        return convert_keys(data)


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
class CompletedStage:
    """A completed build stage with timing and status."""

    name: str
    stage_id: str
    elapsed_seconds: float
    status: StageStatus  # Use StageStatus enum instead of plain string
    infos: int = 0
    warnings: int = 0
    errors: int = 0
    alerts: int = 0


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
    logs_base: Optional[Path] = None
    workspace_paths: list[Path] = field(default_factory=list)


@dataclass(frozen=True)
class InstalledPackage:
    identifier: str
    version: str
    project_root: str
