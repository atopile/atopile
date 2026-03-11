"""UI sidebar state workflows for the websocket store."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import cast

from atopile.dataclasses import (
    PackageDetails,
    PackagesSummaryData,
    PackageSummaryItem,
    Project,
    UiInstalledPartsData,
    UiMigrationState,
    UiMigrationStep,
    UiMigrationStepResult,
    UiMigrationTopic,
    UiPackageDetailState,
    UiPartDetail,
    UiPartsSearchData,
    UiSidebarDetails,
)
from atopile.model import migrations, packages, parts_search, projects
from atopile.server.ui.store import Store


def clear() -> UiSidebarDetails:
    """Return the empty sidebar details state."""
    return UiSidebarDetails()


async def show_package_details(
    store: Store,
    project_root: str | None,
    package_id: str,
    *,
    action_error: str | None = None,
) -> None:
    """Set package details loading state and then resolve the details."""
    packages_summary = cast(PackagesSummaryData, store.get("packages_summary"))
    state = package_details_loading(
        cast(UiSidebarDetails, store.get("sidebar_details")),
        packages_summary,
        project_root,
        package_id,
        action_error=action_error,
    )
    store.set("sidebar_details", state)
    store.set(
        "sidebar_details",
        await load_package_details(
            state,
            packages_summary,
            project_root,
            package_id,
            action_error=action_error,
        ),
    )


async def show_part_details(
    store: Store,
    *,
    project_root: str | None,
    lcsc: str | None,
    identifier: str | None = None,
    installed: bool = False,
    seed: UiPartDetail | None = None,
    action_error: str | None = None,
) -> None:
    """Set part details loading state and then resolve the details."""
    state = part_details_loading(
        cast(UiSidebarDetails, store.get("sidebar_details")),
        cast(UiInstalledPartsData, store.get("installed_parts")),
        cast(UiPartsSearchData, store.get("parts_search")),
        project_root=project_root,
        lcsc=lcsc,
        identifier=identifier,
        installed=installed,
        seed=seed,
        action_error=action_error,
    )
    store.set("sidebar_details", state)
    store.set(
        "sidebar_details",
        await load_part_details(
            state,
            project_root=project_root,
            lcsc=lcsc,
            identifier=identifier,
            installed=installed,
            seed=seed,
            action_error=action_error,
        ),
    )


async def show_migration_details(store: Store, project_root: str) -> None:
    """Set migration details loading state and then resolve the details."""
    projects_state = cast(list[Project], store.get("projects"))
    state = migration_details_loading(
        cast(UiSidebarDetails, store.get("sidebar_details")),
        projects_state,
        project_root,
    )
    store.set("sidebar_details", state)
    store.set(
        "sidebar_details",
        await load_migration_details(
            state,
            projects_state,
            project_root,
        ),
    )


def package_details_loading(
    state: UiSidebarDetails,
    packages_summary: PackagesSummaryData,
    project_root: str | None,
    package_id: str,
    *,
    action_error: str | None = None,
) -> UiSidebarDetails:
    """Set package details into loading state."""
    return _set_package_details(
        state,
        packages_summary,
        project_root,
        package_id,
        loading=True,
        action_error=action_error,
    )


async def load_package_details(
    state: UiSidebarDetails,
    packages_summary: PackagesSummaryData,
    project_root: str | None,
    package_id: str,
    *,
    action_error: str | None = None,
) -> UiSidebarDetails:
    """Load package detail data and return the next sidebar state."""
    try:
        details = await asyncio.to_thread(
            packages.handle_get_package_details,
            package_id,
            Path(project_root) if project_root else None,
            None,
        )
    except Exception as exc:
        return _set_package_details(
            state,
            packages_summary,
            project_root,
            package_id,
            loading=False,
            error=str(exc),
            action_error=action_error,
        )

    if details is None:
        return _set_package_details(
            state,
            packages_summary,
            project_root,
            package_id,
            loading=False,
            error=f"No details found for {package_id}.",
            action_error=action_error,
        )

    return _set_package_details(
        state,
        packages_summary,
        project_root,
        package_id,
        loading=False,
        details=details,
        action_error=action_error,
    )


def part_details_loading(
    state: UiSidebarDetails,
    installed_parts: UiInstalledPartsData,
    search_state: UiPartsSearchData,
    *,
    project_root: str | None,
    lcsc: str | None,
    identifier: str | None = None,
    installed: bool = False,
    seed: UiPartDetail | None = None,
    action_error: str | None = None,
) -> UiSidebarDetails:
    """Set part details into loading state."""
    part = seed or _make_part_seed(
        installed_parts=installed_parts,
        search_state=search_state,
        project_root=project_root,
        identifier=identifier,
        lcsc=lcsc,
        installed=installed,
    )
    return _set_part_details(
        state,
        project_root=project_root,
        lcsc=lcsc,
        part=part,
        loading=bool(lcsc),
        action_error=action_error,
    )


async def load_part_details(
    state: UiSidebarDetails,
    *,
    project_root: str | None,
    lcsc: str | None,
    identifier: str | None = None,
    installed: bool = False,
    seed: UiPartDetail | None = None,
    action_error: str | None = None,
) -> UiSidebarDetails:
    """Load part detail data and return the next sidebar state."""
    base_part = seed or state.part.part
    if not lcsc:
        return _set_part_details(
            state,
            project_root=project_root,
            lcsc=lcsc,
            part=base_part,
            loading=False,
            error="This part does not have an LCSC identifier.",
            action_error=action_error,
        )

    try:
        detail = await asyncio.to_thread(
            parts_search.handle_get_part_details,
            lcsc,
            project_root=project_root,
            identifier=identifier or (base_part.identifier if base_part else None),
            installed=installed,
        )
    except Exception as exc:
        return _set_part_details(
            state,
            project_root=project_root,
            lcsc=lcsc,
            part=base_part,
            loading=False,
            error=str(exc),
            action_error=action_error,
        )

    if detail is None:
        return _set_part_details(
            state,
            project_root=project_root,
            lcsc=lcsc,
            part=base_part,
            loading=False,
            error=f"No details found for {lcsc}.",
            action_error=action_error,
        )

    merged = detail.model_copy(
        update={
            "identifier": (base_part.identifier if base_part else "")
            or detail.identifier
            or detail.mpn
            or identifier
            or lcsc
            or "",
            "lcsc": detail.lcsc or lcsc,
            "path": detail.path or (base_part.path if base_part else None),
            "import_statement": detail.import_statement,
            "installed": installed,
        }
    )
    return _set_part_details(
        state,
        project_root=project_root,
        lcsc=lcsc,
        part=merged,
        loading=False,
        action_error=action_error,
    )


def migration_details_loading(
    state: UiSidebarDetails,
    projects_state: list[Project],
    project_root: str,
) -> UiSidebarDetails:
    """Set migration details into loading state."""
    project = projects.find_project(projects_state, project_root)
    return _set_migration_details(
        state,
        UiMigrationState(
            project_root=project_root,
            project_name=_project_name(project_root, project),
            needs_migration=bool(project and project.needs_migration),
            loading=True,
        ),
    )


async def load_migration_details(
    state: UiSidebarDetails,
    projects_state: list[Project],
    project_root: str,
) -> UiSidebarDetails:
    """Load migration metadata and return the next sidebar state."""
    project = projects.find_project(projects_state, project_root)
    try:
        steps = [
            UiMigrationStep.model_validate(step.to_dict())
            for step in migrations.get_all_steps()
        ]
        topics = [
            UiMigrationTopic.model_validate(topic) for topic in migrations.get_topics()
        ]
    except Exception as exc:
        return _set_migration_details(
            state,
            UiMigrationState(
                project_root=project_root,
                project_name=_project_name(project_root, project),
                needs_migration=bool(project and project.needs_migration),
                loading=False,
                error=str(exc),
            ),
        )

    return _set_migration_details(
        state,
        UiMigrationState(
            project_root=project_root,
            project_name=_project_name(project_root, project),
            needs_migration=bool(project and project.needs_migration),
            steps=steps,
            topics=topics,
            step_results=[UiMigrationStepResult(step_id=step.id) for step in steps],
            loading=False,
        ),
    )


def update_migration_project_state(
    state: UiSidebarDetails,
    projects_state: list[Project],
    project_root: str,
) -> UiSidebarDetails:
    """Refresh migration project metadata after project changes."""
    project = projects.find_project(projects_state, project_root)
    return _set_migration_details(
        state,
        state.migration.model_copy(
            update={
                "project_root": project_root,
                "project_name": _project_name(project_root, project),
                "needs_migration": bool(project and project.needs_migration),
                "loading": False,
            }
        ),
    )


def start_migration_run(
    state: UiSidebarDetails,
    selected_steps: list[str],
) -> UiSidebarDetails:
    """Mark selected migration steps as running."""
    return _set_migration_details(
        state,
        state.migration.model_copy(
            update={
                "step_results": [
                    UiMigrationStepResult(
                        step_id=step.id,
                        status="running" if step.id in selected_steps else "idle",
                    )
                    for step in state.migration.steps
                ],
                "loading": False,
                "running": True,
                "completed": False,
                "error": None,
            }
        ),
    )


def finish_migration_step(
    state: UiSidebarDetails,
    step_id: str,
    *,
    error: str | None,
) -> UiSidebarDetails:
    """Apply the result of a single migration step."""
    status = "error" if error else "success"
    return _set_migration_details(
        state,
        state.migration.model_copy(
            update={
                "step_results": [
                    UiMigrationStepResult(
                        step_id=result.step_id,
                        status=status,
                        error=error,
                    )
                    if result.step_id == step_id
                    else result
                    for result in state.migration.step_results
                ],
                "loading": False,
                "running": True,
                "completed": False,
                "error": None,
            }
        ),
    )


def complete_migration_run(state: UiSidebarDetails) -> tuple[UiSidebarDetails, bool]:
    """Finalize a migration run and report whether it succeeded."""
    has_errors = any(
        result.status == "error" for result in state.migration.step_results
    )
    return (
        _set_migration_details(
            state,
            state.migration.model_copy(
                update={
                    "loading": False,
                    "running": False,
                    "completed": True,
                    "error": None if not has_errors else "Some migration steps failed.",
                }
            ),
        ),
        not has_errors,
    )


def _set_package_details(
    state: UiSidebarDetails,
    packages_summary: PackagesSummaryData,
    project_root: str | None,
    package_id: str,
    *,
    loading: bool,
    error: str | None = None,
    action_error: str | None = None,
    details: PackageDetails | None = None,
) -> UiSidebarDetails:
    return state.model_copy(
        update={
            "view": "package",
            "package": UiPackageDetailState(
                project_root=project_root,
                package_id=package_id,
                summary=_find_package_summary(packages_summary, package_id),
                details=details,
                loading=loading,
                error=error,
                action_error=action_error,
            ),
        }
    )


def _find_package_summary(
    packages_summary: PackagesSummaryData,
    package_id: str,
) -> PackageSummaryItem:
    match = next(
        (pkg for pkg in packages_summary.packages if pkg.identifier == package_id),
        None,
    )
    if match:
        return match

    publisher, _, name = package_id.partition("/")
    return PackageSummaryItem(
        identifier=package_id,
        name=name or package_id,
        publisher=publisher or "unknown",
        installed=False,
    )


def _set_part_details(
    state: UiSidebarDetails,
    *,
    project_root: str | None,
    lcsc: str | None,
    part: UiPartDetail | None,
    loading: bool,
    error: str | None = None,
    action_error: str | None = None,
) -> UiSidebarDetails:
    return state.model_copy(
        update={
            "view": "part",
            "part": state.part.model_copy(
                update={
                    "project_root": project_root,
                    "lcsc": lcsc,
                    "part": part,
                    "loading": loading,
                    "error": error,
                    "action_error": action_error,
                }
            ),
        }
    )


def _make_part_seed(
    *,
    installed_parts: UiInstalledPartsData,
    search_state: UiPartsSearchData,
    project_root: str | None,
    identifier: str | None,
    lcsc: str | None,
    installed: bool,
) -> UiPartDetail:
    installed_match = next(
        (
            part
            for part in installed_parts.parts
            if (identifier and part.identifier == identifier)
            or (lcsc and part.lcsc == lcsc)
        ),
        None,
    )
    if installed_match:
        return UiPartDetail(
            identifier=installed_match.identifier or identifier or lcsc or "",
            lcsc=installed_match.lcsc or lcsc,
            mpn=installed_match.mpn,
            manufacturer=installed_match.manufacturer,
            description=installed_match.description,
            datasheet_url=installed_match.datasheet_url,
            path=installed_match.path,
            installed=installed,
        )

    search_match = next(
        (part for part in search_state.parts if lcsc and part.lcsc == lcsc),
        None,
    )
    if search_match:
        return UiPartDetail(
            identifier=identifier or lcsc or search_match.mpn or "",
            lcsc=lcsc or search_match.lcsc,
            mpn=search_match.mpn,
            manufacturer=search_match.manufacturer,
            description=search_match.description,
            package=search_match.package,
            datasheet_url=search_match.datasheet_url,
            stock=search_match.stock,
            unit_cost=search_match.unit_cost,
            is_basic=search_match.is_basic,
            is_preferred=search_match.is_preferred,
            attributes=search_match.attributes,
            installed=installed,
        )

    return UiPartDetail(
        identifier=identifier or lcsc or "",
        lcsc=lcsc,
        mpn=identifier or lcsc or "",
        installed=installed,
        path=str(Path(project_root) / "parts" / identifier)
        if project_root and installed and identifier
        else None,
    )


def _set_migration_details(
    state: UiSidebarDetails,
    migration: UiMigrationState,
) -> UiSidebarDetails:
    return state.model_copy(update={"view": "migration", "migration": migration})


def _project_name(project_root: str, project: Project | None) -> str:
    return project.name if project else Path(project_root).name
