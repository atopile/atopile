"""
Local package management helpers (installed package inspection).
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

import yaml

from atopile.dataclasses import InstalledPackage, PackageInfo
from . import projects as core_projects

log = logging.getLogger(__name__)


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
    packages_map: dict[str, PackageInfo] = {}

    projects = core_projects.discover_projects_in_paths(paths)

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
    """Install or update a package in a project via `ato add`."""
    cmd = ["ato", "add", package_identifier]
    if version:
        cmd.append(f"@{version}")

    result = subprocess.run(
        cmd,
        cwd=str(project_root),
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr or "ato add failed")


def remove_package_from_project(project_root: Path, package_identifier: str) -> None:
    """Remove a package from a project via `ato remove`."""
    cmd = ["ato", "remove", package_identifier]
    result = subprocess.run(
        cmd,
        cwd=str(project_root),
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr or "ato remove failed")
