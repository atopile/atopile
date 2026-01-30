"""
WebSocket action handlers.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import threading
import time
from pathlib import Path

from atopile.buildutil import generate_build_id, generate_build_timestamp
from atopile.config import ProjectConfig
from atopile.dataclasses import AppContext, Build, BuildStatus, Log
from atopile.logging import BuildLogger
from atopile.model import builds as builds_domain
from atopile.model.build_queue import (
    _build_queue,
)
from atopile.model.model_state import model_state
from atopile.server import path_utils
from atopile.server.client_state import client_state
from atopile.server.connections import server_state
from atopile.server.core import packages as core_packages
from atopile.server.core import projects as core_projects
from atopile.server.domains import artifacts as artifacts_domain
from atopile.server.domains import packages as packages_domain
from atopile.server.domains import parts as parts_domain
from atopile.server.domains import projects as projects_domain
from atopile.server.events import event_bus

log = logging.getLogger(__name__)


def _handle_build_sync(payload: dict) -> dict:
    """
    Sync helper for build action - handles all blocking I/O and lock operations.
    Returns a result dict.
    """
    log.info(f"_handle_build_sync called with payload: {payload}")
    project_root = payload.get("projectRoot") or payload.get("project_root", "")
    targets = payload.get("targets", [])
    entry = payload.get("entry")
    standalone = payload.get("standalone", False)
    frozen = payload.get("frozen", False)
    level = payload.get("level")
    payload_id = payload.get("id")
    payload_label = payload.get("label")
    log.info(
        f"Parsed: project_root={project_root}, targets={targets}, level={level}, id={payload_id}"  # noqa: E501
    )

    build_all_targets = False
    if level and payload_id:
        if level == "project":
            project_root = payload_id
            if not targets:
                build_all_targets = True
        elif level == "build":
            if ":" in payload_id:
                parts = payload_id.rsplit(":", 1)
                project_root = parts[0]
                if not payload_label and len(parts) > 1:
                    payload_label = parts[1]
            else:
                project_root = payload_id

            if payload_label and not targets:
                targets = [payload_label]
        elif level == "symbol":
            project_root = payload_id

    if not project_root:
        return {
            "success": False,
            "error": "Missing projectRoot",
            "needs_state_sync": False,
        }

    if not targets and not build_all_targets:
        targets = ["default"]

    project_path = Path(project_root) if project_root else Path("")
    if project_root and not project_path.exists():
        if "/" in project_root and not project_root.startswith("/"):
            package_identifier = project_root
            ws_path = model_state.workspace_path
            packages = packages_domain.get_all_installed_packages(
                [ws_path] if ws_path else []
            )
            pkg = packages.get(package_identifier)
            if pkg and pkg.installed_in:
                consuming_project = pkg.installed_in[0]
                package_dir = (
                    Path(consuming_project) / ".ato" / "modules" / package_identifier
                )
                if package_dir.exists():
                    project_root = str(package_dir)
                    project_path = package_dir
                else:
                    project_root = consuming_project
                    project_path = Path(project_root)

    if not project_root or not project_path.exists():
        return {
            "success": False,
            "error": f"Project path does not exist: {project_root}",
            "needs_state_sync": False,
        }

    if standalone:
        if not entry:
            return {
                "success": False,
                "error": "Standalone builds require an entry point",
                "needs_state_sync": False,
            }
        entry_file = entry.split(":")[0] if ":" in entry else entry
        entry_path = project_path / entry_file
        if not entry_path.exists():
            return {
                "success": False,
                "error": f"Entry file not found: {entry_path}",
                "needs_state_sync": False,
            }
    else:
        ato_yaml_path = project_path / "ato.yaml"
        if not ato_yaml_path.exists():
            return {
                "success": False,
                "error": f"No ato.yaml found in: {project_root}",
                "needs_state_sync": False,
            }

        if build_all_targets:
            log.info(
                f"build_all_targets=True, loading ProjectConfig from {project_path}"
            )
            try:
                project_config = ProjectConfig.from_path(project_path)
                all_targets = (
                    list(project_config.builds.keys()) if project_config else []
                )
                log.info(f"Found targets: {all_targets}")
                if all_targets:
                    build_ids = []
                    for target_name in all_targets:
                        existing_id = _build_queue.is_duplicate(
                            project_root, target_name, entry
                        )
                        if existing_id:
                            build_ids.append(existing_id)
                            continue

                        timestamp = generate_build_timestamp()
                        build_id = generate_build_id(
                            project_root, target_name, timestamp
                        )

                        _build_queue.enqueue(
                            Build(
                                build_id=build_id,
                                project_root=project_root,
                                target=target_name,
                                timestamp=timestamp,
                                entry=entry,
                                standalone=standalone,
                                frozen=frozen,
                                status=BuildStatus.QUEUED,
                                started_at=time.time(),
                            )
                        )

                        log.info(
                            f"Enqueueing build {build_id} for target {target_name}"
                        )
                        build_ids.append(build_id)

                    log.info(f"All {len(build_ids)} builds enqueued successfully")
                    return {
                        "success": True,
                        "message": f"Queued {len(build_ids)} builds for all targets",
                        "build_ids": build_ids,
                        "targets": all_targets,
                    }
                targets = ["default"]
            except Exception as exc:
                log.warning(
                    f"Failed to read targets from ato.yaml: {exc}, falling back to 'default'"  # noqa: E501
                )
                targets = ["default"]

    # Create one build per target
    build_ids = []
    build_label = entry if standalone else "project"
    timestamp = generate_build_timestamp()

    for target_name in targets:
        existing_build_id = _build_queue.is_duplicate(project_root, target_name, entry)
        if existing_build_id:
            build_ids.append(existing_build_id)
            continue

        log.info(f"Creating build for target={target_name}, entry={entry}")
        build_id = generate_build_id(project_root, target_name, timestamp)
        log.info(f"Allocated build_id={build_id}")
        _build_queue.enqueue(
            Build(
                build_id=build_id,
                project_root=project_root,
                target=target_name,
                timestamp=timestamp,
                entry=entry,
                standalone=standalone,
                frozen=frozen,
                status=BuildStatus.QUEUED,
                started_at=time.time(),
            )
        )

        log.info(f"Enqueueing build {build_id}")
        build_ids.append(build_id)

    log.info(f"All {len(build_ids)} builds enqueued successfully")

    if len(build_ids) == 1:
        return {
            "success": True,
            "message": f"Build queued for {build_label}",
            "build_id": build_ids[0],
        }
    else:
        return {
            "success": True,
            "message": f"Queued {len(build_ids)} builds for {build_label}",
            "build_ids": build_ids,
        }


def _resolve_build_target(
    project_root: str, build_id: str, payload: dict
) -> tuple[str | None, str | None]:
    target_name = payload.get("targetName") or payload.get("target")
    resolved_project_root = project_root

    if build_id:
        build_info = builds_domain.handle_get_build_info(build_id)
        if isinstance(build_info, dict):
            target_name = (
                target_name
                or build_info.get("target")
                or build_info.get("name")
                or build_info.get("build_name")
            )
            resolved_project_root = (
                resolved_project_root
                or build_info.get("project_root")
                or build_info.get("projectRoot")
            )

    return target_name, resolved_project_root


async def handle_data_action(action: str, payload: dict, ctx: AppContext) -> dict:
    """Handle data-fetching actions invoked from WebSocket clients."""
    log.info(f"handle_data_action called: action={action}, payload={payload}")

    try:
        if action == "refreshProjects":
            if ctx.workspace_paths:
                await asyncio.to_thread(
                    core_projects.discover_projects_in_paths, ctx.workspace_paths
                )
                await server_state.emit_event("projects_changed")
            return {"success": True}

        if action == "createProject":
            parent_directory = payload.get("parentDirectory")
            name = payload.get("name")

            if not parent_directory:
                if ctx.workspace_paths:
                    parent_directory = str(ctx.workspace_paths[0])
                else:
                    return {"success": False, "error": "Missing parentDirectory"}

            try:
                # Run blocking project creation in thread pool
                project_dir, project_name = await asyncio.to_thread(
                    core_projects.create_project, Path(parent_directory), name
                )
            except ValueError as exc:
                return {"success": False, "error": str(exc)}

            await handle_data_action("refreshProjects", {}, ctx)
            return {
                "success": True,
                "project_root": str(project_dir),
                "project_name": project_name,
            }

        if action == "refreshPackages":
            scan_path = ctx.workspace_paths[0] if ctx.workspace_paths else None
            await packages_domain.refresh_packages_state(scan_path=scan_path)
            return {"success": True}

        if action == "searchPackages":
            query = payload.get("query", "")
            path = payload.get("path")
            scan_path = packages_domain.resolve_scan_path(ctx, path)
            result = await asyncio.to_thread(
                packages_domain.handle_search_registry, query, scan_path
            )
            return {"success": True, **result.model_dump(by_alias=True)}

        if action == "refreshStdlib":
            await server_state.emit_event("stdlib_changed")
            return {"success": True}

        if action == "buildPackage":
            package_id = payload.get("packageId", "")
            entry = payload.get("entry")

            if not package_id:
                return {"success": False, "error": "Missing packageId"}

            return await handle_data_action(
                "build",
                {
                    "projectRoot": package_id,
                    "entry": entry,
                    "standalone": entry is not None,
                },
                ctx,
            )

        if action == "build":
            log.info(f"Build action starting with payload: {payload}")
            try:
                # Run blocking build preparation in thread pool
                log.info("Running _handle_build_sync in thread pool...")
                result = await asyncio.to_thread(_handle_build_sync, payload)
                log.info(f"_handle_build_sync returned: {result}")

                return result
            except Exception as build_exc:
                log.exception(f"Build action failed with exception: {build_exc}")
                return {"success": False, "error": str(build_exc)}

        if action == "cancelBuild":
            build_id = payload.get("buildId", "")
            if not build_id:
                return {"success": False, "error": "Missing buildId"}

            if not _build_queue.find_build(build_id):
                return {"success": False, "error": f"Build not found: {build_id}"}

            success = _build_queue.cancel_build(build_id)
            if success:
                return {"success": True, "message": f"Build {build_id} cancelled"}
            return {
                "success": False,
                "message": f"Build {build_id} cannot be cancelled (already completed)",
            }

        if action == "fetchModules":
            project_root = payload.get("projectRoot", "")
            if not project_root:
                return {"success": True, "info": "No project specified"}

            project_path = Path(project_root)
            if not await asyncio.to_thread(project_path.exists):
                return {
                    "success": False,
                    "error": f"Project not found: {project_root}",
                }

            response = await asyncio.to_thread(
                projects_domain.handle_get_modules, project_root
            )
            if response:
                return {"success": True, **response.model_dump(by_alias=True)}
            return {"success": False, "error": "No modules found"}

        if action == "checkEntry":
            project_root = payload.get("project_root") or payload.get("projectRoot", "")
            entry = payload.get("entry") or payload.get("entryPoint") or ""
            if not project_root or not entry:
                return {
                    "success": False,
                    "error": "Missing project_root or entry",
                }

            project_path = Path(project_root)
            if not await asyncio.to_thread(project_path.exists):
                return {
                    "success": False,
                    "error": f"Project not found: {project_root}",
                }

            file_part = entry.split(":", 1)[0]
            file_exists = False
            if file_part:
                file_path = (project_path / file_part).resolve()
                file_exists = await asyncio.to_thread(file_path.exists)

            module_exists = False
            try:
                response = await asyncio.to_thread(
                    projects_domain.handle_get_modules, project_root
                )
                modules = response.modules if response else []
                module_exists = any(m.entry == entry for m in modules)
            except Exception:
                module_exists = False

            return {
                "success": True,
                "file_exists": file_exists,
                "module_exists": module_exists,
            }

        if action == "getPackageDetails":
            package_id = payload.get("packageId", "")
            version = payload.get("version")
            if package_id:
                # Run blocking registry fetch in thread pool
                scan_path = ctx.workspace_paths[0] if ctx.workspace_paths else None
                details = await asyncio.to_thread(
                    packages_domain.handle_get_package_details,
                    package_id,
                    scan_path,
                    ctx,
                    version,
                )
                if details:
                    return {
                        "success": True,
                        "details": details.model_dump(by_alias=True),
                    }
            return {"success": False, "error": f"Package not found: {package_id}"}

        if action == "clearPackageDetails":
            return {"success": True}

        if action == "getBomTargets":
            project_root = payload.get("projectRoot", "")
            if not project_root:
                return {"success": False, "error": "Missing projectRoot"}
            try:
                result = await asyncio.to_thread(
                    artifacts_domain.handle_get_bom_targets, project_root
                )
                return {"success": True, **result}
            except Exception as exc:
                return {"success": False, "error": str(exc)}

        if action == "refreshBOM":
            project_root = payload.get("projectRoot", "")
            target = payload.get("target", "default")

            if not project_root:
                return {"success": False, "error": "No project selected"}

            project_path = Path(project_root)
            bom_path = project_path / "build" / "builds" / target / f"{target}.bom.json"

            # Run blocking file check in thread pool
            if not await asyncio.to_thread(bom_path.exists):
                return {"success": True, "info": "BOM not found"}

            try:
                # Run blocking file read in thread pool
                bom_text = await asyncio.to_thread(bom_path.read_text)
                bom_json = json.loads(bom_text)
                return {"success": True, "bom": bom_json}
            except Exception as exc:
                return {"success": False, "error": str(exc)}

        if action == "refreshProblems":
            await server_state.emit_event("problems_changed")
            return {"success": True}

        if action == "fetchVariables":
            project_root = payload.get("projectRoot", "")
            target = payload.get("target", "default")

            if not project_root:
                return {"success": False, "error": "No project specified"}

            project_path = Path(project_root)
            variables_path = (
                project_path / "build" / "builds" / target / f"{target}.variables.json"
            )

            # Run blocking file check in thread pool
            if not await asyncio.to_thread(variables_path.exists):
                return {"success": True, "info": "Variables not found"}

            try:
                # Run blocking file read in thread pool
                variables_text = await asyncio.to_thread(variables_path.read_text)
                variables_json = json.loads(variables_text)
                return {"success": True, "variables": variables_json}
            except Exception as exc:
                return {"success": False, "error": str(exc)}

        if action == "getVariablesTargets":
            project_root = payload.get("projectRoot", "")
            if not project_root:
                return {"success": False, "error": "Missing projectRoot"}
            try:
                result = await asyncio.to_thread(
                    artifacts_domain.handle_get_variables_targets, project_root
                )
                return {"success": True, **result}
            except Exception as exc:
                return {"success": False, "error": str(exc)}

        if action == "installPackage":
            package_id = payload.get("packageId", "")
            project_root = payload.get("projectRoot", "")
            version = payload.get("version")

            if not package_id or not project_root:
                return {
                    "success": False,
                    "error": "Missing packageId or projectRoot",
                }

            project_path = Path(project_root)
            # Run blocking path checks in thread pool
            if not await asyncio.to_thread(project_path.exists):
                return {
                    "success": False,
                    "error": f"Project not found: {project_root}",
                }

            ato_yaml_path = project_path / "ato.yaml"
            if not await asyncio.to_thread(ato_yaml_path.exists):
                return {
                    "success": False,
                    "error": f"No ato.yaml in: {project_root}",
                }

            # Build package spec with optional version
            pkg_spec = f"{package_id}@{version}" if version else package_id

            # Create a logger for this action - logs to central SQLite DB
            action_logger = BuildLogger.get(
                project_path=project_root,
                target="package-install",
                stage="install",
            )

            action_logger.info(
                f"Installing {pkg_spec}...",
                audience=Log.Audience.USER,
            )

            def run_install():
                try:
                    try:
                        core_packages.install_package_to_project(
                            project_path, package_id, version
                        )
                        action_logger.info(
                            f"Successfully installed {pkg_spec}",
                            audience=Log.Audience.USER,
                        )
                        loop = event_bus._event_loop

                        async def finalize_install() -> None:
                            # Clear module introspection cache to pick up new packages
                            from atopile.server.module_introspection import (
                                clear_module_cache,
                            )

                            clear_module_cache()
                            await packages_domain.refresh_packages_state(
                                scan_path=project_path
                            )
                            # Emit packages_changed so UI refreshes
                            await server_state.emit_event(
                                "packages_changed",
                                {"package_id": package_id, "installed": True},
                            )
                            await server_state.emit_event(
                                "project_dependencies_changed",
                                {"project_root": project_root},
                            )

                        if loop and loop.is_running():
                            asyncio.run_coroutine_threadsafe(
                                finalize_install(),
                                loop,
                            )
                    except Exception as exc:
                        error_msg = str(exc)[:500] or "Unknown error"
                        action_logger.error(
                            f"Failed to install {pkg_spec}: {error_msg}",
                            audience=Log.Audience.USER,
                        )
                        loop = event_bus._event_loop
                        if loop and loop.is_running():
                            error_detail = f"Failed to install {pkg_spec}: {error_msg}"
                            asyncio.run_coroutine_threadsafe(
                                server_state.emit_event(
                                    "packages_changed",
                                    {
                                        "error": error_detail,
                                        "package_id": package_id,
                                    },
                                ),
                                loop,
                            )
                except Exception as exc:
                    action_logger.error(
                        f"Failed to install {pkg_spec}: {exc}",
                        audience=Log.Audience.USER,
                    )
                    loop = event_bus._event_loop
                    if loop and loop.is_running():
                        error_detail = f"Failed to install {pkg_spec}: {exc}"
                        asyncio.run_coroutine_threadsafe(
                            server_state.emit_event(
                                "packages_changed",
                                {
                                    "error": error_detail,
                                    "package_id": package_id,
                                },
                            ),
                            loop,
                        )
                finally:
                    action_logger.flush()

            threading.Thread(target=run_install, daemon=True).start()

            return {
                "success": True,
                "message": f"Installing {package_id}...",
                "build_id": action_logger.build_id,
            }

        if action == "changeDependencyVersion":
            package_id = payload.get("identifier") or payload.get("packageId", "")
            project_root = payload.get("projectRoot") or payload.get("projectId", "")
            version = payload.get("version")

            if not package_id or not project_root or not version:
                return {
                    "success": False,
                    "error": "Missing identifier, projectRoot, or version",
                }

            project_path = Path(project_root)
            if not await asyncio.to_thread(project_path.exists):
                return {
                    "success": False,
                    "error": f"Project not found: {project_root}",
                }

            ato_yaml_path = project_path / "ato.yaml"
            if not await asyncio.to_thread(ato_yaml_path.exists):
                return {
                    "success": False,
                    "error": f"No ato.yaml in: {project_root}",
                }

            # Ensure dependency is direct (present in ato.yaml)
            try:
                data, _ = core_projects._load_ato_yaml(project_path)
                deps = data.get("dependencies", [])
                is_direct = False
                if isinstance(deps, list):
                    for dep in deps:
                        if isinstance(dep, str):
                            dep_id = dep.rsplit("@", 1)[0] if "@" in dep else dep
                            if dep_id == package_id:
                                is_direct = True
                                break
                        elif isinstance(dep, dict):
                            dep_id = dep.get("identifier") or dep.get("name")
                            if dep_id == package_id:
                                is_direct = True
                                break
                elif isinstance(deps, dict):
                    is_direct = package_id in deps
            except Exception:
                is_direct = False

            if not is_direct:
                return {
                    "success": False,
                    "error": (
                        "Cannot change version for a transitive dependency. "
                        "Update the direct parent dependency instead."
                    ),
                }

            # Run remove + install sequentially in background
            action_logger = BuildLogger.get(
                project_path=project_root,
                target="package-version",
                stage="install",
            )
            action_logger.info(
                f"Changing {package_id} to {version}...",
                audience=Log.Audience.USER,
            )

            def run_change():
                try:
                    core_packages.remove_package_from_project(project_path, package_id)
                    core_packages.install_package_to_project(
                        project_path, package_id, version
                    )
                    action_logger.info(
                        f"Successfully installed {package_id}@{version}",
                        audience=Log.Audience.USER,
                    )
                    loop = event_bus._event_loop

                    async def finalize_change() -> None:
                        from atopile.server.module_introspection import (
                            clear_module_cache,
                        )

                        clear_module_cache()
                        await packages_domain.refresh_packages_state(
                            scan_path=project_path
                        )
                        await server_state.emit_event(
                            "project_dependencies_changed",
                            {"project_root": project_root},
                        )

                    if loop and loop.is_running():
                        asyncio.run_coroutine_threadsafe(finalize_change(), loop)
                except Exception as exc:
                    error_msg = str(exc)[:500] or "Unknown error"
                    action_logger.error(
                        f"Failed to change {package_id} to {version}: {error_msg}",
                        audience=Log.Audience.USER,
                    )
                    loop = event_bus._event_loop
                    if loop and loop.is_running():
                        error_detail = (
                            f"Failed to change {package_id} to {version}: {error_msg}"
                        )
                        asyncio.run_coroutine_threadsafe(
                            server_state.emit_event(
                                "packages_changed",
                                {
                                    "error": error_detail,
                                    "package_id": package_id,
                                },
                            ),
                            loop,
                        )
                finally:
                    action_logger.flush()

            threading.Thread(target=run_change, daemon=True).start()

            return {
                "success": True,
                "message": f"Changing {package_id} to {version}...",
                "build_id": action_logger.build_id,
            }

        if action == "removePackage":
            log.info("removePackage action handler started")
            package_id = payload.get("packageId", "")
            project_root = payload.get("projectRoot", "")
            log.info(
                f"removePackage: package_id={package_id}, project_root={project_root}"
            )

            if not package_id or not project_root:
                return {
                    "success": False,
                    "error": "Missing packageId or projectRoot",
                }

            project_path = Path(project_root)
            log.info(f"removePackage: checking if path exists: {project_path}")
            # Run blocking path check in thread pool
            if not await asyncio.to_thread(project_path.exists):
                log.warning(f"removePackage: project path not found: {project_root}")
                return {
                    "success": False,
                    "error": f"Project not found: {project_root}",
                }

            log.info("removePackage: path exists, creating op tracking entry")
            # Get op_id first (it has its own lock internally)
            op_id = packages_domain.next_package_op_id("pkg-remove")
            with packages_domain._package_op_lock:
                packages_domain._active_package_ops[op_id] = {
                    "action": "remove",
                    "status": "running",
                    "package": package_id,
                    "project_root": project_root,
                    "error": None,
                }
            log.info(f"removePackage: op_id={op_id} created")

            log.info(f"removePackage: package_id={package_id}")

            log.info("removePackage: defining run_remove function")

            async def refresh_deps_after_remove():
                """Refresh project dependencies after package removal."""
                from atopile.server.domains.projects import _build_dependencies
                from atopile.server.module_introspection import clear_module_cache

                # Clear module introspection cache since packages changed
                clear_module_cache()
                log.info(f"Refreshing dependencies for project: {project_root}")

                await asyncio.to_thread(_build_dependencies, project_path)
                log.info("Dependencies refreshed after removal")

                await server_state.emit_event(
                    "project_dependencies_changed",
                    {"project_root": project_root},
                )

            def run_remove():
                try:
                    log.info(f"Removing {package_id} from {project_root}")
                    core_packages.remove_package_from_project(project_path, package_id)
                    log.info("ato remove completed successfully")
                    with packages_domain._package_op_lock:
                        packages_domain._active_package_ops[op_id]["status"] = "success"
                    loop = event_bus._event_loop
                    if loop and loop.is_running():
                        # Refresh global packages state
                        asyncio.run_coroutine_threadsafe(
                            packages_domain.refresh_packages_state(), loop
                        )
                        # Refresh project-specific dependencies
                        asyncio.run_coroutine_threadsafe(
                            refresh_deps_after_remove(), loop
                        )
                    else:
                        log.warning("Event loop not available to refresh state")
                except Exception as exc:
                    error_msg = str(exc)[:500] or "Unknown error"
                    log.exception(f"Exception in run_remove: {error_msg}")
                    with packages_domain._package_op_lock:
                        packages_domain._active_package_ops[op_id]["status"] = "failed"
                        packages_domain._active_package_ops[op_id]["error"] = error_msg
                    loop = event_bus._event_loop
                    if loop and loop.is_running():
                        asyncio.run_coroutine_threadsafe(
                            server_state.emit_event(
                                "packages_changed",
                                {
                                    "error": error_msg,
                                    "package_id": package_id,
                                },
                            ),
                            loop,
                        )

            log.info("removePackage: starting background thread")
            threading.Thread(target=run_remove, daemon=True).start()
            log.info("removePackage: thread started, returning success")

            return {
                "success": True,
                "message": f"Removing {package_id}...",
                "op_id": op_id,
            }

        if action == "fetchFiles":
            project_root = payload.get("projectRoot", "")
            if not project_root:
                return {"success": True, "info": "No project specified"}

            project_path = Path(project_root)
            # Run blocking path check in thread pool
            if not await asyncio.to_thread(project_path.exists):
                return {
                    "success": False,
                    "error": f"Project not found: {project_root}",
                }

            # Run blocking file tree build in thread pool
            file_tree = await asyncio.to_thread(
                core_projects.build_file_tree, project_path, project_path
            )
            return {
                "success": True,
                "files": [node.model_dump(by_alias=True) for node in file_tree],
            }

        if action == "fetchDependencies":
            project_root = payload.get("projectRoot", "")
            if not project_root:
                return {"success": True, "info": "No project specified"}

            project_path = Path(project_root)
            # Run blocking path check in thread pool
            if not await asyncio.to_thread(project_path.exists):
                return {
                    "success": False,
                    "error": f"Project not found: {project_root}",
                }

            from atopile.server.domains.projects import _build_dependencies

            dependencies = await asyncio.to_thread(_build_dependencies, project_path)
            return {"success": True, "dependencies": dependencies}

        if action == "fetchBuilds":
            project_root = payload.get("projectRoot", "")
            if not project_root:
                return {"success": True, "info": "No project specified"}

            project_path = Path(project_root)
            if not await asyncio.to_thread(project_path.exists):
                return {
                    "success": False,
                    "error": f"Project not found: {project_root}",
                }

            data, _ = core_projects._load_ato_yaml(project_path)
            builds = []
            for name, config in (data.get("builds") or {}).items():
                if isinstance(config, dict):
                    entry = config.get("entry", "")
                else:
                    entry = str(config)
                last_build = core_projects._load_last_build_for_target(
                    project_path, name
                )
                builds.append(
                    {
                        "name": name,
                        "entry": entry,
                        "root": project_root,
                        "lastBuild": last_build.model_dump(by_alias=True)
                        if last_build
                        else None,
                    }
                )

            return {"success": True, "builds": builds}

        if action == "getModuleChildren":
            project_root = payload.get("projectRoot", "")
            entry_point = payload.get("entryPoint", "")
            max_depth = int(payload.get("maxDepth", 2))
            if not project_root or not entry_point:
                return {"success": False, "error": "Missing projectRoot or entryPoint"}
            from atopile.server.module_introspection import introspect_module

            max_depth = max(0, min(5, max_depth))
            result = await asyncio.to_thread(
                introspect_module, Path(project_root), entry_point, max_depth
            )
            if result is None:
                return {
                    "success": False,
                    "error": f"Could not introspect module: {entry_point}",
                }
            return {
                "success": True,
                "children": [child.model_dump(by_alias=True) for child in result],
            }

        if action == "getModuleChildrenForFile":
            project_root = payload.get("projectRoot", "")
            file_path = payload.get("filePath", "")
            max_depth = int(payload.get("maxDepth", 2))
            if not project_root or not file_path:
                return {"success": False, "error": "Missing projectRoot or filePath"}

            project_path = Path(project_root)
            if not await asyncio.to_thread(project_path.exists):
                return {
                    "success": False,
                    "error": f"Project not found: {project_root}",
                }

            from atopile.server.module_introspection import (
                introspect_module_definition,
            )

            max_depth = max(0, min(5, max_depth))
            file_rel = None
            try:
                file_rel = str(Path(file_path).resolve().relative_to(project_path))
            except Exception:
                file_rel = None

            response = await asyncio.to_thread(
                projects_domain.handle_get_modules, project_root
            )
            modules = response.modules if response else []
            if file_rel:
                modules = [m for m in modules if m.file == file_rel]
            else:
                modules = [m for m in modules if m.file and file_path.endswith(m.file)]

            enriched = [
                introspect_module_definition(project_path, module, max_depth)
                for module in modules
            ]

            return {
                "success": True,
                "modules": [module.model_dump(by_alias=True) for module in enriched],
            }

        if action == "getBuildsByProject":
            project_root = payload.get("projectRoot")
            target = payload.get("target")
            limit = int(payload.get("limit", 50))
            result = await asyncio.to_thread(
                builds_domain.handle_get_builds_by_project, project_root, target, limit
            )
            return {"success": True, **result}

        if action == "getMaxConcurrentSetting":
            try:
                result = await asyncio.to_thread(
                    builds_domain.handle_get_max_concurrent_setting
                )
                return {"success": True, "setting": result}
            except Exception as exc:
                return {"success": False, "error": str(exc)}

        if action == "setMaxConcurrentSetting":
            try:
                data = {k: v for k, v in payload.items() if k != "requestId"}
                use_default = data.get("useDefault", data.get("use_default", True))
                custom_value = data.get("customValue", data.get("custom_value", None))
                request = builds_domain.MaxConcurrentRequest(
                    use_default=bool(use_default),
                    custom_value=custom_value,
                )
                result = await asyncio.to_thread(
                    builds_domain.handle_set_max_concurrent_setting,
                    request,
                )
                return {"success": True, "setting": result}
            except Exception as exc:
                return {"success": False, "error": str(exc)}

        if action == "fetchLcscParts":
            lcsc_ids = payload.get("lcscIds", [])
            project_root = payload.get("projectRoot")
            target = payload.get("target")
            if not lcsc_ids:
                return {"success": False, "error": "Missing lcscIds"}
            try:
                result = await asyncio.to_thread(
                    parts_domain.handle_get_lcsc_parts,
                    lcsc_ids,
                    project_root=project_root,
                    target=target,
                )
                return {"success": True, **result}
            except Exception as exc:
                return {"success": False, "error": str(exc)}

        if action == "addBuildTarget":
            try:
                data = {k: v for k, v in payload.items() if k != "requestId"}
                result = await asyncio.to_thread(
                    projects_domain.handle_add_build_target,
                    projects_domain.AddBuildTargetRequest(**data),
                )
                return {"success": True, **result.model_dump(by_alias=True)}
            except Exception as exc:
                return {"success": False, "error": str(exc)}

        if action == "updateBuildTarget":
            try:
                data = {k: v for k, v in payload.items() if k != "requestId"}
                result = await asyncio.to_thread(
                    projects_domain.handle_update_build_target,
                    projects_domain.UpdateBuildTargetRequest(**data),
                )
                return {"success": True, **result.model_dump(by_alias=True)}
            except Exception as exc:
                return {"success": False, "error": str(exc)}

        if action == "deleteBuildTarget":
            try:
                data = {k: v for k, v in payload.items() if k != "requestId"}
                result = await asyncio.to_thread(
                    projects_domain.handle_delete_build_target,
                    projects_domain.DeleteBuildTargetRequest(**data),
                )
                return {"success": True, **result.model_dump(by_alias=True)}
            except Exception as exc:
                return {"success": False, "error": str(exc)}

        if action == "updateDependencyVersion":
            try:
                data = {k: v for k, v in payload.items() if k != "requestId"}
                result = await asyncio.to_thread(
                    projects_domain.handle_update_dependency_version,
                    projects_domain.UpdateDependencyVersionRequest(**data),
                )
                return {"success": True, **result.model_dump(by_alias=True)}
            except Exception as exc:
                return {"success": False, "error": str(exc)}

        if action == "runTests":
            import hashlib
            import os
            from datetime import datetime

            test_node_ids = payload.get("testNodeIds", [])
            pytest_args = payload.get("pytestArgs", "")
            env_vars = payload.get("env", {})  # Custom env vars (e.g., ConfigFlags)

            if not test_node_ids:
                return {"success": False, "error": "No tests specified"}

            # Generate test_run_id upfront so we can return it immediately
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            hash_input = f"pytest:{timestamp}"
            test_run_id = hashlib.sha256(hash_input.encode()).hexdigest()[:16]

            # Get workspace path for running tests
            if model_state.workspace_path:
                workspace_path = str(model_state.workspace_path)
            else:
                workspace_path = os.getcwd()

            def run_tests_background():
                try:
                    # Change to workspace directory for test runner
                    original_cwd = os.getcwd()
                    os.chdir(workspace_path)

                    # Add workspace to sys.path for imports
                    if workspace_path not in sys.path:
                        sys.path.insert(0, workspace_path)

                    # Import and run the test runner
                    from test.runner.main import main as test_runner_main

                    # Build args: pytest args + test node IDs
                    args = []
                    if pytest_args.strip():
                        args.extend(pytest_args.strip().split())
                    args.extend(test_node_ids)

                    log.info(f"Starting test run {test_run_id} with args: {args}")
                    if env_vars:
                        log.info(f"Custom env vars: {list(env_vars.keys())}")

                    # Run the test runner with the pre-generated test_run_id
                    test_runner_main(
                        args=args,
                        test_run_id=test_run_id,
                        extra_env=env_vars if env_vars else None,
                    )

                except Exception as exc:
                    log.exception(f"Test run {test_run_id} failed: {exc}")
                finally:
                    # Restore original working directory
                    try:
                        os.chdir(original_cwd)
                    except Exception:
                        pass

            # Run tests in background thread
            threading.Thread(target=run_tests_background, daemon=True).start()

            return {
                "success": True,
                "message": f"Started test run with {len(test_node_ids)} tests",
                "test_run_id": test_run_id,
            }

        if action == "uiLog":
            level = payload.get("level", "info")
            message = payload.get("message", "")
            lowered = message.lower()
            if any(
                token in lowered
                for token in (
                    "kicanvas:parser",
                    "kicanvas:project",
                    ".kicad_pcb",
                    ".kicad_sch",
                    ".kicad_pro",
                    "model-viewer",
                    ".glb",
                    "gltf",
                    "three.js",
                )
            ):
                return {"success": True}
            log_method = getattr(log, level, log.info)
            if len(message) > 1000:
                message = f"{message[:1000]}… (truncated)"
            log_method(f"[ui] {message}")
            return {"success": True}

        if action == "ping":
            return {"success": True}

        if action == "openFile":
            file_path = payload.get("file")
            line = payload.get("line")
            column = payload.get("column")

            if not file_path:
                return {"success": False, "error": "Missing file path"}

            workspace_path = ctx.workspace_paths[0] if ctx.workspace_paths else None
            resolved = path_utils.resolve_workspace_file(file_path, workspace_path)
            if not resolved:
                return {
                    "success": False,
                    "error": f"File not found: {file_path}",
                }

            await server_state.emit_event(
                "open_file",
                {"path": str(resolved), "line": line, "column": column},
            )
            return {"success": True}

        if action == "openSource":
            project_root = payload.get("projectId", "")
            entry = payload.get("entry", "")

            if not project_root or not entry:
                return {"success": False, "error": "Missing projectId or entry"}

            project_path = Path(project_root)
            entry_path = path_utils.resolve_entry_path(project_path, entry)
            if not entry_path or not entry_path.exists():
                return {
                    "success": False,
                    "error": f"Entry file not found: {entry_path}",
                }

            await server_state.emit_event("open_file", {"path": str(entry_path)})
            return {"success": True}

        if action == "openLayout":
            project_root = payload.get("projectId", "")
            build_id = payload.get("buildId", "")

            target_name, resolved_project_root = _resolve_build_target(
                project_root, build_id, payload
            )
            if not resolved_project_root or not target_name:
                return {
                    "success": False,
                    "error": "Missing projectId or buildId/target",
                }

            project_path = Path(resolved_project_root)
            target = path_utils.resolve_layout_path(project_path, target_name)
            if not target or not target.exists():
                return {
                    "success": False,
                    "error": f"Layout not found for target: {target_name}",
                }

            await server_state.emit_event("open_layout", {"path": str(target)})
            return {"success": True}

        if action == "openKiCad":
            project_root = payload.get("projectId", "")
            build_id = payload.get("buildId", "")

            target_name, resolved_project_root = _resolve_build_target(
                project_root, build_id, payload
            )
            if not resolved_project_root or not target_name:
                return {
                    "success": False,
                    "error": "Missing projectId or buildId/target",
                }

            project_path = Path(resolved_project_root)
            target = path_utils.resolve_layout_path(project_path, target_name)
            if not target or not target.exists():
                return {
                    "success": False,
                    "error": f"Layout not found for target: {target_name}",
                }

            await server_state.emit_event("open_kicad", {"path": str(target)})
            return {"success": True}

        if action == "open3D":
            project_root = payload.get("projectId", "")
            build_id = payload.get("buildId", "")

            target_name, resolved_project_root = _resolve_build_target(
                project_root, build_id, payload
            )
            if not resolved_project_root or not target_name:
                return {
                    "success": False,
                    "error": "Missing projectId or buildId/target",
                }

            project_path = Path(resolved_project_root)
            target = path_utils.resolve_3d_path(project_path, target_name)
            if not target or not target.exists():
                return {
                    "success": False,
                    "error": f"3D view not found for target: {target_name}",
                }

            await server_state.emit_event("open_3d", {"path": str(target)})
            return {"success": True}

        elif action == "setLogViewCurrentId":
            build_id = payload.get("buildId")
            stage = payload.get("stage")
            client_state.log_view_current_id = build_id
            client_state.log_view_current_stage = stage
            await server_state.emit_event(
                "log_view_current_id_changed",
                {"buildId": build_id, "stage": stage},
            )
            return {"success": True}

        elif action == "getLogViewCurrentId":
            return {
                "success": True,
                "buildId": client_state.log_view_current_id,
                "stage": client_state.log_view_current_stage,
            }

        elif action == "setAtopileSource":
            await server_state.emit_event(
                "atopile_config_changed",
                {"source": payload.get("source", "release")},
            )
            return {"success": True}

        elif action == "setAtopileLocalPath":
            await server_state.emit_event(
                "atopile_config_changed",
                {
                    "local_path": payload.get("path"),
                    "source": "local",  # Also set source to 'local' so the UI knows
                },
            )
            return {"success": True}

        elif action == "setAtopileInstalling":
            installing = payload.get("installing", False)
            error = payload.get("error")
            await server_state.emit_event(
                "atopile_config_changed",
                {"is_installing": installing, "error": error},
            )
            return {"success": True}

        elif action == "browseAtopilePath":
            return {
                "success": False,
                "error": "browseAtopilePath is not supported in the UI server",
            }

        elif action == "validateAtopilePath":
            from atopile.server.domains import atopile_install

            path = payload.get("path", "")
            result = await atopile_install.validate_local_path(path)
            log.info(f"[validateAtopilePath] path={path}, result={result}")
            return {"success": True, **result}

        elif action == "getAtopileConfig":
            # Return the current atopile config including actual version
            # This is called when WebSocket connects to get the current state
            from atopile import version as ato_version

            try:
                version_obj = ato_version.get_installed_atopile_version()
                actual_version = str(version_obj)
            except Exception:
                actual_version = None

            actual_source = ctx.ato_source or "unknown"
            ui_source = ctx.ato_ui_source or "release"

            # Emit the config so it gets to the frontend
            await server_state.emit_event(
                "atopile_config_changed",
                {
                    "actual_version": actual_version,
                    "actual_source": actual_source,
                    "source": ui_source,
                },
            )
            return {
                "success": True,
                "actual_version": actual_version,
                "actual_source": actual_source,
                "source": ui_source,
            }

        elif action == "setWorkspaceFolders":
            folders = payload.get("folders", [])
            workspace_paths = [Path(f) for f in folders] if folders else []
            ctx.workspace_paths = workspace_paths
            model_state.set_workspace_paths(workspace_paths)
            await handle_data_action("refreshProjects", {}, ctx)
            await handle_data_action("refreshPackages", {}, ctx)
            return {"success": True}

        return {"success": False, "error": f"Unknown action: {action}"}

    except Exception as exc:
        log.error(f"Error in handle_data_action: {exc}")
        return {"success": False, "error": str(exc)}
