"""
Project-related Pydantic schemas.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class BuildTargetStatus(BaseModel):
    """Persisted status from last build of a target."""

    status: str  # 'success', 'warning', 'failed', 'building', 'queued'
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


class Project(BaseModel):
    """A project discovered from ato.yaml."""

    root: str
    name: str
    targets: list[BuildTarget]


class ProjectsResponse(BaseModel):
    """Response for /api/projects endpoint."""

    projects: list[Project]
    total: int


class ModuleDefinition(BaseModel):
    """A module/interface/component definition from an .ato file."""

    name: str
    type: Literal["module", "interface", "component"]
    file: str  # Relative path to the .ato file
    entry: str  # Entry point format: "file.ato:ModuleName"
    line: Optional[int] = None  # Line number where defined
    super_type: Optional[str] = None  # Parent type if extends


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
