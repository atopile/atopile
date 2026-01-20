"""
Pydantic schemas for the dashboard API.

These are the source of truth for API types.
TypeScript types in the frontend should mirror these.
"""

from .project import (
    BuildTarget,
    BuildTargetStatus,
    Project,
    ProjectsResponse,
    ModuleDefinition,
    ModulesResponse,
    FileTreeNode,
    FilesResponse,
    DependencyInfo,
    DependenciesResponse,
)
from .build import (
    BuildStatus,
    StageStatus,
    BuildStage,
    Build,
    BuildRequest,
    BuildResponse,
    BuildStatusResponse,
    LogLevel,
    LogEntry,
    LogCounts,
)
from .package import (
    PackageInfo,
    PackageVersion,
    PackageDetails,
    PackageSummaryItem,
    PackagesResponse,
    PackagesSummaryResponse,
    RegistrySearchResponse,
    PackageActionRequest,
    PackageActionResponse,
    RegistryStatus,
)
from .problem import (
    Problem,
    ProblemFilter,
    ProblemsResponse,
)

__all__ = [
    # Project
    "BuildTarget",
    "BuildTargetStatus",
    "Project",
    "ProjectsResponse",
    "ModuleDefinition",
    "ModulesResponse",
    "FileTreeNode",
    "FilesResponse",
    "DependencyInfo",
    "DependenciesResponse",
    # Build
    "BuildStatus",
    "StageStatus",
    "BuildStage",
    "Build",
    "BuildRequest",
    "BuildResponse",
    "BuildStatusResponse",
    "LogLevel",
    "LogEntry",
    "LogCounts",
    # Package
    "PackageInfo",
    "PackageVersion",
    "PackageDetails",
    "PackageSummaryItem",
    "PackagesResponse",
    "PackagesSummaryResponse",
    "RegistrySearchResponse",
    "PackageActionRequest",
    "PackageActionResponse",
    "RegistryStatus",
    # Problem
    "Problem",
    "ProblemFilter",
    "ProblemsResponse",
]
