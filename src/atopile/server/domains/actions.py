"""
WebSocket action handlers.
"""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
import threading
import time
from pathlib import Path

from atopile.buildutil import generate_build_id, generate_build_timestamp
from atopile.config import ProjectConfig
from atopile.dataclasses import Log
from atopile.logging import BuildLogger
from atopile.server import (
    path_utils,
    problem_parser,
    project_discovery,
)
from atopile.server.app_context import AppContext
from atopile.server.build_queue import (
    _active_builds,
    _build_lock,
    _build_queue,
    _is_duplicate_build,
    _sync_builds_to_state_async,
    cancel_build,
)
from atopile.server.core import projects as core_projects
from atopile.server.domains import artifacts as artifacts_domain
from atopile.server.domains import builds as builds_domain
from atopile.server.domains import packages as packages_domain
from atopile.server.domains import parts as parts_domain
from atopile.server.domains import projects as projects_domain
from atopile.server.state import server_state
from atopile.server.stdlib import get_standard_library

log = logging.getLogger(__name__)


def _handle_build_sync(payload: dict) -> dict:
    """
    Sync helper for build action - handles all blocking I/O and lock operations.
    Returns a result dict. If successful and needs_state_sync is True, caller should
    call _sync_builds_to_state_async().
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
        project_root = server_state._state.selected_project_root or ""

    if not targets:
        targets = server_state._state.selected_target_names or []

    project_path = Path(project_root) if project_root else Path("")
    if project_root and not project_path.exists():
        if "/" in project_root and not project_root.startswith("/"):
            package_identifier = project_root
            packages = server_state._state.packages or []
            pkg = next(
                (p for p in packages if p.identifier == package_identifier),
                None,
            )
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
                        existing_id = _is_duplicate_build(
                            project_root, target_name, entry
                        )
                        if existing_id:
                            build_ids.append(existing_id)
                            continue

                        with _build_lock:
                            timestamp = generate_build_timestamp()
                            build_id = generate_build_id(
                                project_root, target_name, timestamp
                            )
                            _active_builds[build_id] = {
                                "status": "queued",
                                "project_root": project_root,
                                "target": target_name,
                                "entry": entry,
                                "standalone": standalone,
                                "frozen": frozen,
                                "return_code": None,
                                "error": None,
                                "started_at": time.time(),
                                "timestamp": timestamp,
                                "stages": [],
                            }

                        log.info(
                            f"Enqueueing build {build_id} for target {target_name}"
                        )
                        _build_queue.enqueue(build_id)
                        build_ids.append(build_id)

                    log.info(f"All {len(build_ids)} builds enqueued successfully")
                    return {
                        "success": True,
                        "message": f"Queued {len(build_ids)} builds for all targets",
                        "build_ids": build_ids,
                        "targets": all_targets,
                        "needs_state_sync": True,
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
        existing_build_id = _is_duplicate_build(project_root, target_name, entry)
        if existing_build_id:
            build_ids.append(existing_build_id)
            continue

        log.info(f"Creating build for target={target_name}, entry={entry}")
        with _build_lock:
            build_id = generate_build_id(project_root, target_name, timestamp)
            log.info(f"Allocated build_id={build_id}")
            _active_builds[build_id] = {
                "status": "queued",
                "project_root": project_root,
                "target": target_name,
                "entry": entry,
                "standalone": standalone,
                "frozen": frozen,
                "return_code": None,
                "error": None,
                "started_at": time.time(),
                "timestamp": timestamp,
                "stages": [],
            }

        log.info(f"Enqueueing build {build_id}")
        _build_queue.enqueue(build_id)
        build_ids.append(build_id)

    log.info(f"All {len(build_ids)} builds enqueued successfully")

    if len(build_ids) == 1:
        return {
            "success": True,
            "message": f"Build queued for {build_label}",
            "build_id": build_ids[0],
            "needs_state_sync": True,
        }
    else:
        return {
            "success": True,
            "message": f"Queued {len(build_ids)} builds for {build_label}",
            "build_ids": build_ids,
            "needs_state_sync": True,
        }


async def handle_data_action(action: str, payload: dict, ctx: AppContext) -> dict:
    """Handle data-fetching actions invoked from WebSocket clients."""
    log.info(f"handle_data_action called: action={action}, payload={payload}")

    try:
        if action == "refreshProjects":
            scan_paths = ctx.workspace_paths
            if scan_paths:
                from atopile.dataclasses import BuildTarget as StateBuildTarget
                from atopile.dataclasses import Project as StateProject

                # Run blocking project discovery in thread pool
                projects = await asyncio.to_thread(
                    project_discovery.discover_projects_in_paths, scan_paths
                )
                state_projects = [
                    StateProject(
                        root=p.root,
                        name=p.name,
                        targets=[
                            StateBuildTarget(
                                name=t.name,
                                entry=t.entry,
                                root=t.root,
                                last_build=t.last_build,
                            )
                            for t in p.targets
                        ],
                    )
                    for p in projects
                ]
                await server_state.set_projects(state_projects)
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
            await packages_domain.refresh_packages_state(scan_paths=ctx.workspace_paths)
            return {"success": True}

        if action == "searchPackages":
            query = payload.get("query", "")
            paths = payload.get("paths")
            scan_paths = packages_domain.resolve_scan_paths(ctx, paths)
            result = await asyncio.to_thread(
                packages_domain.handle_search_registry, query, scan_paths
            )
            return {"success": True, **result.model_dump(by_alias=True)}

        if action == "refreshStdlib":
            from atopile.dataclasses import StdLibItem as StateStdLibItem

            # Run blocking stdlib fetch in thread pool
            items = await asyncio.to_thread(get_standard_library)
            state_items = [
                StateStdLibItem.model_validate(item.model_dump()) for item in items
            ]
            await server_state.set_stdlib_items(state_items)
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

                # Sync state if build was queued (async operation)
                if result.get("needs_state_sync"):
                    log.info("Syncing builds to state...")
                    await _sync_builds_to_state_async()
                    log.info("State sync complete")

                # Remove internal flag before returning
                result.pop("needs_state_sync", None)
                return result
            except Exception as build_exc:
                log.exception(f"Build action failed with exception: {build_exc}")
                return {"success": False, "error": str(build_exc)}

        if action == "cancelBuild":
            build_id = payload.get("buildId", "")
            if not build_id:
                return {"success": False, "error": "Missing buildId"}

            if build_id not in _active_builds:
                return {"success": False, "error": f"Build not found: {build_id}"}

            success = cancel_build(build_id)
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
                await server_state.set_project_modules(project_root, response.modules)
            return {"success": True}

        if action == "getPackageDetails":
            package_id = payload.get("packageId", "")
            if package_id:
                from atopile.dataclasses import PackageDetails as StatePackageDetails

                # Run blocking registry fetch in thread pool
                details = await asyncio.to_thread(
                    packages_domain.get_package_details_from_registry, package_id
                )
                if details:
                    state_details = StatePackageDetails.model_validate(
                        details.model_dump()
                    )
                    await server_state.set_package_details(state_details)
                    return {
                        "success": True,
                        "details": state_details.model_dump(by_alias=True),
                    }
                else:
                    await server_state.set_package_details(
                        None, f"Package not found: {package_id}"
                    )
            return {"success": False, "error": f"Package not found: {package_id}"}

        if action == "clearPackageDetails":
            await server_state.set_package_details(None)
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
                selected = server_state._state.selected_project_root
                if selected:
                    project_root = selected

            if not project_root:
                await server_state.set_bom_data(None, "No project selected")
                return {"success": False, "error": "No project selected"}

            project_path = Path(project_root)
            bom_path = project_path / "build" / "builds" / target / f"{target}.bom.json"

            # Run blocking file check in thread pool
            if not await asyncio.to_thread(bom_path.exists):
                await server_state.set_bom_data(None, "BOM not found. Run build first.")
                return {"success": True, "info": "BOM not found"}

            try:
                # Run blocking file read in thread pool
                bom_text = await asyncio.to_thread(bom_path.read_text)
                bom_json = json.loads(bom_text)
                await server_state.set_bom_data(bom_json)
                return {"success": True}
            except Exception as exc:
                await server_state.set_bom_data(None, str(exc))
                return {"success": False, "error": str(exc)}

        if action == "refreshProblems":
            from atopile.dataclasses import Problem as StateProblem

            # Run blocking DB query in thread pool
            raw_problems = await asyncio.to_thread(
                problem_parser._load_problems_from_db
            )

            all_problems: list[StateProblem] = []
            for problem in raw_problems:
                all_problems.append(
                    StateProblem(
                        id=problem.id,
                        level=problem.level,
                        message=problem.message,
                        file=problem.file,
                        line=problem.line,
                        column=problem.column,
                        stage=problem.stage,
                        logger=problem.logger,
                        build_name=problem.build_name,
                        project_name=problem.project_name,
                        timestamp=problem.timestamp,
                        ato_traceback=problem.ato_traceback,
                        exc_info=problem.exc_info,
                    )
                )

            await server_state.set_problems(all_problems)
            return {"success": True}

        if action == "fetchVariables":
            project_root = payload.get("projectRoot", "")
            target = payload.get("target", "default")

            if not project_root:
                await server_state.set_variables_data(None, "No project specified")
                return {"success": False, "error": "No project specified"}

            project_path = Path(project_root)
            variables_path = (
                project_path / "build" / "builds" / target / f"{target}.variables.json"
            )

            # Run blocking file check in thread pool
            if not await asyncio.to_thread(variables_path.exists):
                await server_state.set_variables_data(
                    None, "Variables not found. Run build first."
                )
                return {"success": True, "info": "Variables not found"}

            try:
                # Run blocking file read in thread pool
                variables_text = await asyncio.to_thread(variables_path.read_text)
                variables_json = json.loads(variables_text)
                await server_state.set_variables_data(variables_json)
                return {"success": True}
            except Exception as exc:
                await server_state.set_variables_data(None, str(exc))
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
                await server_state.remove_installing_package(
                    package_id or "<unknown>", "Missing packageId or projectRoot"
                )
                return {
                    "success": False,
                    "error": "Missing packageId or projectRoot",
                }

            project_path = Path(project_root)
            # Run blocking path checks in thread pool
            if not await asyncio.to_thread(project_path.exists):
                await server_state.remove_installing_package(
                    package_id, f"Project not found: {project_root}"
                )
                return {
                    "success": False,
                    "error": f"Project not found: {project_root}",
                }

            ato_yaml_path = project_path / "ato.yaml"
            if not await asyncio.to_thread(ato_yaml_path.exists):
                await server_state.remove_installing_package(
                    package_id, f"No ato.yaml in: {project_root}"
                )
                return {
                    "success": False,
                    "error": f"No ato.yaml in: {project_root}",
                }

            # Build package spec with optional version
            pkg_spec = f"{package_id}@{version}" if version else package_id
            cmd = ["ato", "add", pkg_spec]

            # Create a logger for this action - logs to central SQLite DB
            action_logger = BuildLogger.get(
                project_path=project_root,
                target="package-install",
                stage="install",
            )

            await server_state.add_installing_package(package_id)

            action_logger.info(
                f"Installing {pkg_spec}...",
                audience=Log.Audience.USER,
            )

            def run_install():
                try:
                    result = subprocess.run(
                        cmd,
                        cwd=project_root,
                        capture_output=True,
                        text=True,
                        timeout=120,
                    )
                    if result.returncode == 0:
                        action_logger.info(
                            f"Successfully installed {pkg_spec}",
                            audience=Log.Audience.USER,
                        )
                        loop = server_state._event_loop

                        async def finalize_install() -> None:
                            # Clear module introspection cache to pick up new packages
                            from atopile.server.module_introspection import (
                                clear_module_cache,
                            )

                            clear_module_cache()
                            await packages_domain.refresh_packages_state(
                                scan_paths=[project_path]
                            )
                            await server_state.remove_installing_package(package_id)

                        if loop and loop.is_running():
                            asyncio.run_coroutine_threadsafe(
                                finalize_install(),
                                loop,
                            )
                    else:
                        error_msg = (
                            result.stderr.strip()
                            if result.stderr
                            else result.stdout.strip()
                        )
                        error_msg = error_msg[:500] if error_msg else "Unknown error"
                        action_logger.error(
                            f"Failed to install {pkg_spec}: {error_msg}",
                            audience=Log.Audience.USER,
                        )
                        loop = server_state._event_loop
                        if loop and loop.is_running():
                            asyncio.run_coroutine_threadsafe(
                                server_state.remove_installing_package(
                                    package_id,
                                    f"Failed to install {pkg_spec}: {error_msg}",
                                ),
                                loop,
                            )
                except Exception as exc:
                    action_logger.error(
                        f"Failed to install {pkg_spec}: {exc}",
                        audience=Log.Audience.USER,
                    )
                    loop = server_state._event_loop
                    if loop and loop.is_running():
                        asyncio.run_coroutine_threadsafe(
                            server_state.remove_installing_package(
                                package_id,
                                f"Failed to install {pkg_spec}: {exc}",
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

            return await handle_data_action(
                "installPackage",
                {
                    "packageId": package_id,
                    "projectRoot": project_root,
                    "version": version,
                },
                ctx,
            )

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

            cmd = ["ato", "remove", package_id]
            log.info(f"removePackage: cmd={cmd}")

            log.info("removePackage: defining run_remove function")

            async def refresh_deps_after_remove():
                """Refresh project dependencies after package removal."""
                from atopile.dataclasses import DependencyInfo
                from atopile.server.module_introspection import clear_module_cache

                # Clear module introspection cache since packages changed
                clear_module_cache()
                log.info(f"Refreshing dependencies for project: {project_root}")

                installed = await asyncio.to_thread(
                    packages_domain.get_installed_packages_for_project, project_path
                )
                log.info(f"Found {len(installed)} installed packages after removal")

                dependencies: list[DependencyInfo] = []
                for pkg in installed:
                    parts = pkg.identifier.split("/")
                    publisher = parts[0] if len(parts) > 1 else "unknown"
                    name = parts[-1]
                    dependencies.append(
                        DependencyInfo(
                            identifier=pkg.identifier,
                            version=pkg.version,
                            name=name,
                            publisher=publisher,
                        )
                    )

                await server_state.set_project_dependencies(project_root, dependencies)
                log.info(f"Updated project dependencies state for {project_root}")

            def run_remove():
                try:
                    log.info(f"Running: {' '.join(cmd)} in {project_root}")
                    result = subprocess.run(
                        cmd,
                        cwd=project_root,
                        capture_output=True,
                        text=True,
                        timeout=120,
                    )
                    log.info(
                        f"ato remove completed with return code: {result.returncode}"
                    )
                    if result.stderr:
                        log.debug(f"ato remove stderr: {result.stderr[:500]}")
                    with packages_domain._package_op_lock:
                        if result.returncode == 0:
                            log.info(f"Package {package_id} removed successfully")
                            packages_domain._active_package_ops[op_id]["status"] = (
                                "success"
                            )
                            loop = server_state._event_loop
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
                        else:
                            log.error(f"ato remove failed: {result.stderr[:500]}")
                            packages_domain._active_package_ops[op_id]["status"] = (
                                "failed"
                            )
                            packages_domain._active_package_ops[op_id]["error"] = (
                                result.stderr[:500]
                            )
                except Exception as exc:
                    log.exception(f"Exception in run_remove: {exc}")
                    with packages_domain._package_op_lock:
                        packages_domain._active_package_ops[op_id]["status"] = "failed"
                        packages_domain._active_package_ops[op_id]["error"] = str(exc)

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
            await server_state.set_project_files(project_root, file_tree)
            return {"success": True}

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

            from atopile.server.state import DependencyInfo

            # Run blocking package fetch in thread pool
            installed = await asyncio.to_thread(
                packages_domain.get_installed_packages_for_project, project_path
            )

            dependencies: list[DependencyInfo] = []
            for pkg in installed:
                parts = pkg.identifier.split("/")
                publisher = parts[0] if len(parts) > 1 else "unknown"
                name = parts[-1]

                latest_version = None
                has_update = False
                repository = None

                cached_pkg = server_state.packages_by_id.get(pkg.identifier)
                if cached_pkg:
                    latest_version = cached_pkg.latest_version
                    has_update = packages_domain.version_is_newer(
                        pkg.version, latest_version
                    )
                    repository = cached_pkg.repository

                dependencies.append(
                    DependencyInfo(
                        identifier=pkg.identifier,
                        version=pkg.version,
                        latest_version=latest_version,
                        name=name,
                        publisher=publisher,
                        repository=repository,
                        has_update=has_update,
                    )
                )

            await server_state.set_project_dependencies(project_root, dependencies)
            return {"success": True}

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

        if action == "uiLog":
            level = payload.get("level", "info")
            message = payload.get("message", "")
            log_method = getattr(log, level, log.info)
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

            resolved = path_utils.resolve_workspace_file(file_path, ctx.workspace_paths)
            if not resolved:
                return {
                    "success": False,
                    "error": f"File not found: {file_path}",
                }

            await server_state.set_open_file(
                str(resolved),
                line,
                column,
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

            await server_state.set_open_file(str(entry_path), None, None)
            return {"success": True}

        if action == "openLayout":
            project_root = payload.get("projectId", "")
            build_id = payload.get("buildId", "")

            if not project_root or not build_id:
                return {"success": False, "error": "Missing projectId or buildId"}

            project_path = Path(project_root)
            target = path_utils.resolve_layout_path(project_path, build_id)
            if not target or not target.exists():
                return {
                    "success": False,
                    "error": f"Layout not found for build: {build_id}",
                }

            await server_state.set_open_layout(str(target))
            return {"success": True}

        if action == "openKiCad":
            project_root = payload.get("projectId", "")
            build_id = payload.get("buildId", "")

            if not project_root or not build_id:
                return {"success": False, "error": "Missing projectId or buildId"}

            project_path = Path(project_root)
            target = path_utils.resolve_layout_path(project_path, build_id)
            if not target or not target.exists():
                return {
                    "success": False,
                    "error": f"Layout not found for build: {build_id}",
                }

            await server_state.set_open_kicad(str(target))
            return {"success": True}

        if action == "open3D":
            project_root = payload.get("projectId", "")
            build_id = payload.get("buildId", "")

            if not project_root or not build_id:
                return {"success": False, "error": "Missing projectId or buildId"}

            project_path = Path(project_root)
            target = path_utils.resolve_3d_path(project_path, build_id)
            if not target or not target.exists():
                return {
                    "success": False,
                    "error": f"3D view not found for build: {build_id}",
                }

            await server_state.set_open_3d(str(target))
            return {"success": True}

        # State management actions (previously in state.py)
        elif action == "selectProject":
            await server_state.set_selected_project(payload.get("projectRoot"))
            return {"success": True}

        elif action == "setSelectedTargets":
            await server_state.set_selected_targets(payload.get("targetNames", []))
            return {"success": True}

        elif action == "toggleTarget":
            await server_state.toggle_target(payload.get("targetName", ""))
            return {"success": True}

        elif action == "toggleTargetExpanded":
            await server_state.toggle_target_expanded(payload.get("targetName", ""))
            return {"success": True}

        elif action == "selectBuild":
            await server_state.set_selected_build(payload.get("buildName"))
            return {"success": True}

        elif action == "toggleProblemLevelFilter":
            level = payload.get("level")
            if level:
                await server_state.toggle_problem_level_filter(level)
            return {"success": True}

        elif action == "setDeveloperMode":
            enabled = payload.get("enabled", False)
            await server_state.set_developer_mode(enabled)
            return {"success": True}

        elif action == "setAtopileSource":
            await server_state.set_atopile_source(payload.get("source", "release"))
            return {"success": True}

        elif action == "setAtopileVersion":
            await server_state.set_atopile_version(payload.get("version", ""))
            return {"success": True}

        elif action == "setAtopieBranch":
            await server_state.set_atopile_branch(payload.get("branch"))
            return {"success": True}

        elif action == "setAtopileLocalPath":
            await server_state.set_atopile_local_path(payload.get("path"))
            return {"success": True}

        elif action == "setAtopileInstalling":
            installing = payload.get("installing", False)
            error = payload.get("error")
            await server_state.set_atopile_installing(installing, error)
            return {"success": True}

        elif action == "browseAtopilePath":
            return {
                "success": False,
                "error": "browseAtopilePath is not supported in the UI server",
            }

        elif action == "refreshAtopileVersions":
            from atopile.server.domains import atopile_install

            versions = await atopile_install.fetch_available_versions()
            await server_state.set_atopile_available_versions(versions)
            return {"success": True, "versions": versions}

        elif action == "refreshAtopileBranches":
            from atopile.server.domains import atopile_install

            branches = await atopile_install.fetch_available_branches()
            await server_state.set_atopile_available_branches(branches)
            return {"success": True, "branches": branches}

        elif action == "validateAtopilePath":
            from atopile.server.domains import atopile_install

            path = payload.get("path", "")
            result = await atopile_install.validate_local_path(path)
            return {"success": True, **result}

        elif action == "refreshDetectedInstallations":
            from atopile.server.domains import atopile_install

            installations = await asyncio.to_thread(
                atopile_install.detect_local_installations
            )
            await server_state.set_atopile_detected_installations(installations)
            return {"success": True, "installations": installations}

        elif action == "setWorkspaceFolders":
            folders = payload.get("folders", [])
            paths = [Path(p) for p in folders if p]
            ctx.workspace_paths = paths
            server_state.set_workspace_paths(paths)
            await handle_data_action("refreshProjects", {}, ctx)
            await handle_data_action("refreshPackages", {}, ctx)
            return {"success": True}

        return {"success": False, "error": f"Unknown action: {action}"}

    except Exception as exc:
        log.error(f"Error in handle_data_action: {exc}")
        return {"success": False, "error": str(exc)}
