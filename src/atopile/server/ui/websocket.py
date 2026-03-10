"""WebSocket transport for the UI-facing core server API.

This module owns connection lifecycle, subscriptions, and dispatch only.
UI-specific state and interaction helpers live in `src/atopile/server/ui`.
Domain logic lives in `src/atopile/model`.
"""

# TODO: Replace raw websocket action payload decoding with typed request models.

from __future__ import annotations

import asyncio
import base64
import json
import logging
from pathlib import Path
from typing import Any, cast

import websockets
from websockets.asyncio.server import ServerConnection

from atopile.dataclasses import (
    AddBuildTargetRequest,
    BuildRequest,
    CreateProjectRequest,
    DeleteBuildTargetRequest,
    OpenLayoutRequest,
    PackagesSummaryData,
    Project,
    UiBuildLogRequest,
    UiInstalledPartsData,
    UiLogEntry,
    UiLogsErrorMessage,
    UiLogsStreamMessage,
    UiPartDetail,
    UiPartsSearchData,
    UiSidebarDetails,
    UpdateBuildTargetRequest,
)
from atopile.model import (
    artifacts,
    builds,
    file_ops,
    migrations,
    packages,
    parts,
    parts_search,
    projects,
    stdlib,
)
from atopile.model.build_queue import BuildQueue, _build_queue
from atopile.model.builds import (
    get_active_builds,
    get_finished_builds,
    handle_start_build,
    resolve_layout_path,
)
from atopile.model.file_watcher import FileWatcher
from atopile.model.module_introspection import introspect_module_definition
from atopile.model.sqlite import Logs
from atopile.server import dev_tools
from atopile.server.domains.vscode_bridge import VscodeBridge
from atopile.server.ui import remote_assets, sidebar
from atopile.server.ui.store import Store

log = logging.getLogger(__name__)

STREAM_POLL_INTERVAL = 0.25  # seconds
EXTENSION_SESSION_ID = "extension"


class CoreSocket:
    """Manages WebSocket connections and dispatches actions."""

    def __init__(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._clients: set[ServerConnection] = set()
        self._subscriptions: dict[ServerConnection, dict[str, set[str]]] = {}
        self._log_tasks: dict[ServerConnection, dict[str, asyncio.Task]] = {}
        self._discovery_paths: list[Path] = []
        self._vscode_bridge = VscodeBridge()
        self._store = Store()
        self._store.on_change = self._on_store_change
        self._project_files = FileWatcher(
            "project-files",
            paths=[],
            on_change=lambda result: self._store.set(
                "project_files", result.tree or []
            ),
            glob="**/*",
            debounce_s=0.1,
            mode="tree",
        )
        self._store.set("current_builds", get_active_builds())
        self._store.set("previous_builds", get_finished_builds())
        self.bind_build_queue(_build_queue)

    # -- Client lifecycle --------------------------------------------------

    async def handle_client(self, ws: ServerConnection) -> None:
        path = getattr(getattr(ws, "request", None), "path", None)
        if path not in {None, "/atopile-ui"}:
            await ws.close(code=4000, reason="unknown path")
            return

        self._clients.add(ws)
        self._subscriptions[ws] = {}
        self._log_tasks[ws] = {}
        self._vscode_bridge.add_client(ws)

        try:
            async for raw in ws:
                msg = json.loads(raw)
                keys = msg.get("keys")
                self._log_websocket_event(
                    "recv",
                    session_id=self._session_id(msg),
                    type=msg.get("type"),
                    action=msg.get("action"),
                    request_id=msg.get("requestId"),
                    ok=msg.get("ok"),
                    key_count=len(keys) if isinstance(keys, list) else None,
                )
                match msg.get("type"):
                    case "subscribe":
                        await self._handle_subscribe(ws, msg)
                    case "action":
                        await self._dispatch(ws, msg)
                    case "extension_response":
                        response = self._vscode_bridge.handle_response(
                            ws, self._session_id(msg), msg
                        )
                        if response is not None:
                            await self._send_message(ws, response)

        except websockets.ConnectionClosed:
            pass
        finally:
            self._clients.discard(ws)
            self._subscriptions.pop(ws, None)
            self._vscode_bridge.remove_client(ws)
            for task in self._log_tasks.pop(ws, {}).values():
                task.cancel()

    async def _handle_subscribe(
        self, ws: ServerConnection, msg: dict[str, Any]
    ) -> None:
        session_id = self._session_id(msg)
        keys = {str(key) for key in msg.get("keys", [])}
        self._subscriptions.setdefault(ws, {})[session_id] = keys
        for key in keys:
            field_name = self._store.require_field_name(key)
            await self._send_state(
                ws, session_id, field_name, self._store.dump(field_name)
            )

    def _sidebar_details_state(self) -> UiSidebarDetails:
        return cast(UiSidebarDetails, self._store.get("sidebar_details"))

    def _projects_state(self) -> list[Project]:
        return cast(list[Project], self._store.get("projects"))

    @staticmethod
    def _request_key(msg: dict[str, Any]) -> str:
        payload = {
            key: value
            for key, value in msg.items()
            if key not in {"type", "action", "requestId", "sessionId"}
        }
        return json.dumps(payload, separators=(",", ":"))

    def _log_websocket_event(self, event: str, **fields: Any) -> None:
        if fields.get("action") == "vscode.log":
            return
        details = " ".join(
            f"{key}={value}" for key, value in fields.items() if value is not None
        )
        if details:
            log.info("WebSocket %s %s", event, details)
            return
        log.info("WebSocket %s", event)

    async def _show_package_details(
        self,
        project_root: str | None,
        package_id: str,
        *,
        action_error: str | None = None,
    ) -> None:
        packages_summary = cast(
            PackagesSummaryData, self._store.get("packages_summary")
        )
        state = sidebar.package_details_loading(
            self._sidebar_details_state(),
            packages_summary,
            project_root,
            package_id,
            action_error=action_error,
        )
        self._store.set("sidebar_details", state)
        self._store.set(
            "sidebar_details",
            await sidebar.load_package_details(
                state,
                packages_summary,
                project_root,
                package_id,
                action_error=action_error,
            ),
        )

    async def _show_part_details(
        self,
        *,
        project_root: str | None,
        lcsc: str | None,
        identifier: str | None = None,
        installed: bool = False,
        seed: UiPartDetail | None = None,
        action_error: str | None = None,
    ) -> None:
        state = sidebar.part_details_loading(
            self._sidebar_details_state(),
            cast(UiInstalledPartsData, self._store.get("installed_parts")),
            cast(UiPartsSearchData, self._store.get("parts_search")),
            project_root=project_root,
            lcsc=lcsc,
            identifier=identifier,
            installed=installed,
            seed=seed,
            action_error=action_error,
        )
        self._store.set("sidebar_details", state)
        self._store.set(
            "sidebar_details",
            await sidebar.load_part_details(
                state,
                project_root=project_root,
                lcsc=lcsc,
                identifier=identifier,
                installed=installed,
                seed=seed,
                action_error=action_error,
            ),
        )

    async def _show_migration_details(self, project_root: str) -> None:
        state = sidebar.migration_details_loading(
            self._sidebar_details_state(),
            self._projects_state(),
            project_root,
        )
        self._store.set("sidebar_details", state)
        self._store.set(
            "sidebar_details",
            await sidebar.load_migration_details(
                state,
                self._projects_state(),
                project_root,
            ),
        )

    async def _refresh_projects(self) -> list[Project]:
        result = await asyncio.to_thread(
            projects.handle_get_projects, self._discovery_paths
        )
        self._store.set("projects", result.projects)
        return result.projects

    async def _refresh_project_entry(self, project_root: str) -> None:
        replacement = await asyncio.to_thread(projects.handle_get_project, project_root)
        if replacement is None:
            return
        self._store.set(
            "projects",
            projects.replace_project(self._projects_state(), replacement),
        )

    # -- Action dispatch ---------------------------------------------------

    async def _dispatch(self, ws: ServerConnection, msg: dict) -> None:
        session_id = self._session_id(msg)
        action = str(msg.get("action", ""))
        if self._vscode_bridge.handles(action):
            await self._send_message(
                ws, self._vscode_bridge.forward_request(ws, session_id, msg)
            )
            return

        match action:
            case "getRemoteAsset":
                request_key = self._request_key(msg)
                asset = await remote_assets.proxy_remote_asset(
                    str(msg.get("url", "")),
                    str(msg.get("filename")) if msg.get("filename") else None,
                )
                self._store.set(
                    "blob_asset",
                    {
                        "action": action,
                        "requestKey": request_key,
                        **asset,
                    },
                )
                return

            case "getPartModelData":
                lcsc_id = str(msg.get("lcsc", ""))
                request_key = self._request_key(msg)
                model = await asyncio.to_thread(
                    parts_search.handle_get_part_model,
                    lcsc_id,
                )
                if not model:
                    raise ValueError(f"3D model not found: {lcsc_id}")
                data, name = model
                self._store.set(
                    "blob_asset",
                    {
                        "action": action,
                        "requestKey": request_key,
                        "contentType": "model/step",
                        "filename": name,
                        "data": base64.b64encode(data).decode("ascii"),
                    },
                )
                return

            case "selectProject":
                project_root = msg.get("projectRoot") or None
                self._store.merge(
                    "project_state",
                    {
                        "selectedProject": project_root,
                        "selectedTarget": None,
                    },
                )
                if project_root:
                    await self._project_files.watch([Path(project_root)])
                else:
                    self._store.set("project_files", [])
                return

            case "selectTarget":
                self._store.merge(
                    "project_state",
                    {
                        "selectedTarget": msg.get("target") or None,
                    },
                )
                return

            case "setLogViewCurrentId":
                self._store.merge(
                    "project_state",
                    {
                        "logViewBuildId": msg.get("buildId") or None,
                        "logViewStage": msg.get("stage") or None,
                    },
                )
                return

            case "resolverInfo":
                self._store.merge(
                    "core_status",
                    {
                        "uvPath": msg.get("uvPath", ""),
                        "atoBinary": msg.get("atoBinary", ""),
                        "mode": msg.get("mode", "production"),
                        "version": msg.get("version", ""),
                        "coreServerPort": msg.get("coreServerPort", 0),
                        "error": None,
                    },
                )
                return

            case "coreStartupError":
                self._store.merge("core_status", {"error": msg.get("message")})
                return

            case "extensionSettings":
                self._store.merge(
                    "extension_settings",
                    {
                        "devPath": msg.get("devPath", ""),
                        "autoInstall": msg.get("autoInstall", True),
                    },
                )
                return

            case "updateExtensionSetting":
                key = msg.get("key")
                if isinstance(key, str):
                    self._store.merge("extension_settings", {key: msg.get("value")})
                return

            case "setActiveFile":
                self._store.merge(
                    "project_state",
                    {
                        "activeFilePath": msg.get("filePath"),
                    },
                )
                return

            case "discoverProjects":
                self._discovery_paths = [Path(p) for p in msg.get("paths", []) if p]
                projects_result = projects.handle_get_projects(self._discovery_paths)
                self._store.set("projects", projects_result.projects)
                return

            case "createProject":
                request = CreateProjectRequest(
                    parent_directory=str(msg.get("parentDirectory") or ""),
                    name=(
                        str(msg.get("name"))
                        if isinstance(msg.get("name"), str) and msg.get("name")
                        else None
                    ),
                )
                create_result = await asyncio.to_thread(
                    projects.handle_create_project, request
                )
                await self._refresh_projects()
                self._store.merge(
                    "project_state",
                    {
                        "selectedProject": create_result.project_root,
                        "selectedTarget": None,
                    },
                )
                return

            case "addBuildTarget":
                request = AddBuildTargetRequest(
                    project_root=str(msg.get("projectRoot") or ""),
                    name=str(msg.get("name") or ""),
                    entry=str(msg.get("entry") or ""),
                )
                add_result = await asyncio.to_thread(
                    projects.handle_add_build_target, request
                )
                await self._refresh_project_entry(request.project_root)
                self._store.merge(
                    "project_state",
                    {
                        "selectedProject": request.project_root,
                        "selectedTarget": add_result.target,
                    },
                )
                return

            case "updateBuildTarget":
                request = UpdateBuildTargetRequest(
                    project_root=str(msg.get("projectRoot") or ""),
                    old_name=str(msg.get("oldName") or ""),
                    new_name=(
                        str(msg.get("newName"))
                        if isinstance(msg.get("newName"), str) and msg.get("newName")
                        else None
                    ),
                    new_entry=(
                        str(msg.get("newEntry"))
                        if isinstance(msg.get("newEntry"), str)
                        else None
                    ),
                )
                update_result = await asyncio.to_thread(
                    projects.handle_update_build_target, request
                )
                await self._refresh_project_entry(request.project_root)
                project_state = cast(dict[str, Any], self._store.dump("project_state"))
                if project_state.get("selectedProject") == request.project_root and (
                    project_state.get("selectedTarget") == request.old_name
                ):
                    self._store.merge(
                        "project_state",
                        {"selectedTarget": update_result.target or request.old_name},
                    )
                return

            case "deleteBuildTarget":
                request = DeleteBuildTargetRequest(
                    project_root=str(msg.get("projectRoot") or ""),
                    name=str(msg.get("name") or ""),
                )
                await asyncio.to_thread(projects.handle_delete_build_target, request)
                await self._refresh_project_entry(request.project_root)
                project_state = cast(dict[str, Any], self._store.dump("project_state"))
                selected_project = project_state.get("selectedProject")
                selected_target = project_state.get("selectedTarget")
                if (
                    selected_project == request.project_root
                    and selected_target == request.name
                ):
                    project = projects.find_project(
                        self._projects_state(), request.project_root
                    )
                    self._store.merge(
                        "project_state",
                        {
                            "selectedTarget": (
                                project.targets[0].name
                                if project and project.targets
                                else None
                            ),
                        },
                    )
                return

            case "checkEntry":
                project_root = str(msg.get("projectRoot") or "")
                entry = str(msg.get("entry") or "").strip()
                project = projects.find_project(self._projects_state(), project_root)
                result = await asyncio.to_thread(
                    projects.handle_check_entry,
                    project_root,
                    entry,
                    project.targets if project else None,
                )
                self._store.set(
                    "entry_check",
                    {
                        "projectRoot": project_root or None,
                        "entry": entry,
                        **result,
                    },
                )
                return

            case "listFiles":
                project_root = msg.get("projectRoot", "")
                if project_root:
                    await self._project_files.watch([Path(project_root)])
                else:
                    self._store.set("project_files", [])
                return

            case "createFile":
                requested_path = str(msg.get("path") or "")
                created_path = await asyncio.to_thread(
                    file_ops.create_file,
                    requested_path,
                )
                self._store.set(
                    "file_action",
                    {
                        "action": "create_file",
                        "path": created_path,
                        "isFolder": False,
                    },
                )
                return

            case "createFolder":
                requested_path = str(msg.get("path") or "")
                created_path = await asyncio.to_thread(
                    file_ops.create_folder,
                    requested_path,
                )
                self._store.set(
                    "file_action",
                    {
                        "action": "create_folder",
                        "path": created_path,
                        "isFolder": True,
                    },
                )
                return

            case "renamePath":
                requested_path = str(msg.get("path") or "")
                new_path = str(msg.get("newPath") or "")
                renamed_path = await asyncio.to_thread(
                    file_ops.rename_path,
                    requested_path,
                    new_path,
                )
                self._store.set(
                    "file_action",
                    {
                        "action": "rename",
                        "path": renamed_path,
                        "isFolder": Path(renamed_path).is_dir(),
                    },
                )
                return

            case "deletePath":
                requested_path = str(msg.get("path") or "")
                await asyncio.to_thread(file_ops.delete_path, requested_path)
                self._store.set(
                    "file_action",
                    {
                        "action": "delete",
                        "path": requested_path,
                        "isFolder": False,
                    },
                )
                return

            case "duplicatePath":
                requested_path = str(msg.get("path") or "")
                duplicated_path = await asyncio.to_thread(
                    file_ops.duplicate_path,
                    requested_path,
                )
                self._store.set(
                    "file_action",
                    {
                        "action": "duplicate",
                        "path": duplicated_path,
                        "isFolder": Path(duplicated_path).is_dir(),
                    },
                )
                return

            case "startBuild":
                request = BuildRequest(
                    project_root=msg.get("projectRoot", ""),
                    targets=msg.get("targets", []),
                    include_targets=msg.get("includeTargets", []),
                    exclude_targets=msg.get("excludeTargets", []),
                )
                handle_start_build(request)
                return

            case "cancelBuild":
                build_id = str(msg.get("buildId") or "")
                await asyncio.to_thread(builds.handle_cancel_build, build_id)
                return

            case "openLayout":
                request = OpenLayoutRequest.model_validate(msg)
                layout_path = await self._open_layout(request)
                self._store.set(
                    "layout_data",
                    {
                        "projectRoot": request.project_root,
                        "target": request.target,
                        "path": str(layout_path),
                    },
                )
                return

            case "getPackagesSummary":
                project_root = msg.get("projectRoot", "")
                root = Path(project_root) if project_root else None
                packages_result = await asyncio.to_thread(
                    packages.handle_packages_summary, root
                )
                self._store.set("packages_summary", packages_result)
                return

            case "showPackageDetails":
                await self._show_package_details(
                    msg.get("projectRoot") or None,
                    str(msg.get("packageId", "")),
                )
                return

            case "closeSidebarDetails":
                self._store.set("sidebar_details", sidebar.clear())
                return

            case "installPackage":
                project_root = Path(msg.get("projectRoot", ""))
                pkg_id = msg.get("packageId", "")
                version = msg.get("version")
                await asyncio.to_thread(
                    packages.install_package_to_project,
                    project_root,
                    pkg_id,
                    version,
                )
                packages_result = await asyncio.to_thread(
                    packages.handle_packages_summary, project_root
                )
                self._store.set("packages_summary", packages_result)
                current = self._sidebar_details_state()
                package_state = current.package
                if (
                    current.view == "package"
                    and package_state.package_id == pkg_id
                    and package_state.project_root == str(project_root)
                ):
                    await self._show_package_details(
                        str(project_root),
                        str(pkg_id),
                    )
                return

            case "removePackage":
                project_root = Path(msg.get("projectRoot", ""))
                pkg_id = msg.get("packageId", "")
                await asyncio.to_thread(
                    packages.remove_package_from_project,
                    project_root,
                    pkg_id,
                )
                packages_result = await asyncio.to_thread(
                    packages.handle_packages_summary, project_root
                )
                self._store.set("packages_summary", packages_result)
                current = self._sidebar_details_state()
                package_state = current.package
                if (
                    current.view == "package"
                    and package_state.package_id == pkg_id
                    and package_state.project_root == str(project_root)
                ):
                    await self._show_package_details(
                        str(project_root),
                        str(pkg_id),
                    )
                return

            case "getStdlib":
                type_filter = msg.get("typeFilter")
                search = msg.get("search")
                stdlib_result = await asyncio.to_thread(
                    stdlib.handle_get_stdlib, type_filter, search
                )
                self._store.set("stdlib_data", stdlib_result)
                return

            case "getStructure":
                project_root = msg.get("projectRoot", "")
                type_filter = msg.get("typeFilter")
                modules_result = await asyncio.to_thread(
                    projects.handle_get_modules, project_root, type_filter
                )
                if modules_result:
                    enriched = []
                    for mod in modules_result.modules:
                        enriched_mod = await asyncio.to_thread(
                            introspect_module_definition,
                            Path(project_root),
                            mod,
                        )
                        enriched.append(enriched_mod)
                    data = {
                        "modules": [m.model_dump() for m in enriched],
                        "total": len(enriched),
                    }
                else:
                    data = {"modules": [], "total": 0}
                self._store.set("structure_data", data)
                return

            case "searchParts":
                query = msg.get("query", "")
                limit = msg.get("limit", 50)
                parts_result, search_error = await asyncio.to_thread(
                    parts_search.handle_search_parts,
                    query,
                    limit=limit,
                )
                self._store.set(
                    "parts_search", {"parts": parts_result, "error": search_error}
                )
                return

            case "getInstalledParts":
                project_root = msg.get("projectRoot", "")
                installed_parts = await asyncio.to_thread(
                    parts_search.handle_list_installed_parts,
                    project_root,
                )
                self._store.set("installed_parts", {"parts": installed_parts})
                return

            case "showPartDetails":
                await self._show_part_details(
                    project_root=msg.get("projectRoot") or None,
                    identifier=msg.get("identifier"),
                    lcsc=msg.get("lcsc"),
                    installed=bool(msg.get("installed")),
                )
                return

            case "installPart":
                project_root = msg.get("projectRoot", "")
                lcsc = msg.get("lcsc", "")
                await asyncio.to_thread(
                    parts_search.handle_install_part,
                    lcsc,
                    project_root,
                )
                installed_parts = await asyncio.to_thread(
                    parts_search.handle_list_installed_parts,
                    project_root,
                )
                self._store.set("installed_parts", {"parts": installed_parts})
                current = self._sidebar_details_state()
                part_state = current.part
                if (
                    current.view == "part"
                    and part_state.lcsc == lcsc
                    and part_state.project_root == project_root
                ):
                    part = part_state.part
                    await self._show_part_details(
                        project_root=project_root,
                        identifier=part.identifier if part else None,
                        lcsc=lcsc,
                        installed=True,
                        seed=part.model_copy(update={"installed": True})
                        if part
                        else None,
                    )
                return

            case "uninstallPart":
                project_root = msg.get("projectRoot", "")
                lcsc = msg.get("lcsc", "")
                await asyncio.to_thread(
                    parts_search.handle_uninstall_part,
                    lcsc,
                    project_root,
                )
                installed_parts = await asyncio.to_thread(
                    parts_search.handle_list_installed_parts,
                    project_root,
                )
                self._store.set("installed_parts", {"parts": installed_parts})
                current = self._sidebar_details_state()
                part_state = current.part
                if (
                    current.view == "part"
                    and part_state.lcsc == lcsc
                    and part_state.project_root == project_root
                ):
                    part = part_state.part
                    await self._show_part_details(
                        project_root=project_root,
                        identifier=part.identifier if part else None,
                        lcsc=lcsc,
                        installed=False,
                        seed=part.model_copy(update={"installed": False})
                        if part
                        else None,
                    )
                return

            case "showMigrationDetails":
                project_root = str(msg.get("projectRoot", ""))
                if project_root:
                    await self._show_migration_details(project_root)
                return

            case "runMigration" | "migrateProjectSteps":
                project_root = str(msg.get("projectRoot", ""))
                selected_steps = [str(step) for step in msg.get("steps", []) if step]
                if not project_root:
                    return
                self._store.set(
                    "sidebar_details",
                    sidebar.start_migration_run(
                        self._sidebar_details_state(),
                        selected_steps,
                    ),
                )
                for step_id in selected_steps:
                    await migrations.get_step(step_id).run(Path(project_root))
                    self._store.set(
                        "sidebar_details",
                        sidebar.finish_migration_step(
                            self._sidebar_details_state(),
                            step_id,
                            error=None,
                        ),
                    )
                final_state, success = sidebar.complete_migration_run(
                    self._sidebar_details_state()
                )
                self._store.set("sidebar_details", final_state)
                await self._refresh_project_entry(project_root)
                self._store.set(
                    "sidebar_details",
                    sidebar.update_migration_project_state(
                        self._sidebar_details_state(),
                        self._projects_state(),
                        project_root,
                    ),
                )
                return

            case "getVariables":
                project_root = msg.get("projectRoot", "")
                target = msg.get("target", "default")
                variables = await asyncio.to_thread(
                    artifacts.handle_get_variables,
                    project_root,
                    target,
                )
                self._store.set("variables_data", variables or {"nodes": []})
                return

            case "getBom":
                project_root = msg.get("projectRoot", "")
                target = msg.get("target", "default")
                bom = await asyncio.to_thread(
                    artifacts.handle_get_bom,
                    project_root,
                    target,
                )
                self._store.set(
                    "bom_data",
                    {
                        "projectRoot": project_root or None,
                        "target": target,
                        **(
                            bom
                            or {
                                "components": [],
                                "totalQuantity": 0,
                                "uniqueParts": 0,
                                "estimatedCost": None,
                                "outOfStock": 0,
                            }
                        ),
                    },
                )
                return

            case "getBuildsByProject":
                project_root = msg.get("projectRoot") or None
                target = msg.get("target") or None
                limit = int(msg.get("limit", 50))
                result = await asyncio.to_thread(
                    builds.handle_get_builds_by_project,
                    project_root,
                    target,
                    limit,
                )
                self._store.set(
                    "builds_by_project_data",
                    {
                        "projectRoot": project_root,
                        "target": target,
                        "limit": limit,
                        "builds": result.get("builds", []),
                    },
                )
                return

            case "fetchLcscParts":
                lcsc_ids = [str(value) for value in msg.get("lcscIds", []) if value]
                project_root = msg.get("projectRoot") or None
                target = msg.get("target") or None
                current_lcsc_parts = cast(
                    dict[str, Any], self._store.dump("lcsc_parts_data")
                )
                current_parts = current_lcsc_parts.get("parts", {})
                if (
                    current_lcsc_parts.get("projectRoot") != project_root
                    or current_lcsc_parts.get("target") != target
                ):
                    current_parts = {}
                result = await asyncio.to_thread(
                    parts.handle_get_lcsc_parts,
                    lcsc_ids,
                    project_root=project_root,
                    target=target,
                )
                self._store.set(
                    "lcsc_parts_data",
                    {
                        "projectRoot": project_root,
                        "target": target,
                        "parts": {**current_parts, **result.get("parts", {})},
                        "loadingIds": [],
                    },
                )
                return

            case "subscribeLogs":
                request = UiBuildLogRequest.model_validate(msg)
                build_id = request.build_id.strip()
                if not build_id:
                    payload = UiLogsErrorMessage(
                        error="buildId is required"
                    ).model_dump(mode="json")
                    payload["sessionId"] = session_id
                    await self._send_message(ws, payload)
                    return
                old_task = self._log_tasks.setdefault(ws, {}).pop(session_id, None)
                if old_task:
                    old_task.cancel()
                query = {
                    "session_id": session_id,
                    "build_id": build_id,
                    "stage": request.stage,
                    "log_levels": request.log_levels,
                    "audience": request.audience,
                    "count": request.count or 1000,
                }
                task = asyncio.create_task(self._log_stream_loop(ws, query))
                self._log_tasks.setdefault(ws, {})[session_id] = task
                return

            case "unsubscribeLogs":
                old_task = self._log_tasks.setdefault(ws, {}).pop(session_id, None)
                if old_task:
                    old_task.cancel()
                return

            case "clearBuildDatabases":
                await asyncio.to_thread(dev_tools.handle_clear_build_databases)
                await self._push_builds()
                return

            case _:
                raise ValueError(f"Unknown action: {action}")
        return

    # -- Log streaming -----------------------------------------------------

    async def _log_stream_loop(self, ws: ServerConnection, query: dict) -> None:
        """Poll SQLite for new logs and push to the client until cancelled."""
        last_id = 0
        try:
            # Send initial batch immediately
            last_id = await self._push_log_stream(ws, query, last_id)
            while True:
                await asyncio.sleep(STREAM_POLL_INTERVAL)
                last_id = await self._push_log_stream(ws, query, last_id)
        except asyncio.CancelledError:
            pass
        except websockets.ConnectionClosed:
            pass

    async def _push_log_stream(
        self, ws: ServerConnection, query: dict, after_id: int
    ) -> int:
        """Fetch new logs from SQLite and push to the client. Returns new cursor."""
        session_id = query.get("session_id", EXTENSION_SESSION_ID)
        build_id = query.get("build_id", "")
        stage = query.get("stage") or None
        log_levels = query.get("log_levels") or None
        audience = query.get("audience") or None
        count = query.get("count", 1000)

        logs, new_last_id = await asyncio.to_thread(
            Logs.fetch_chunk,
            build_id,
            stage=stage,
            levels=log_levels,
            audience=audience,
            after_id=after_id,
            count=count,
        )

        if logs:
            payload = UiLogsStreamMessage(
                logs=[UiLogEntry.model_validate(log) for log in logs],
                last_id=new_last_id,
            ).model_dump(mode="json")
            payload["sessionId"] = session_id
            await self._send_message(ws, payload)
            return new_last_id

        return after_id

    # -- Build queue integration -------------------------------------------

    def bind_build_queue(self, build_queue: BuildQueue) -> None:
        """Register as the listener for build queue changes."""
        loop = asyncio.get_running_loop()

        def _on_change(build_id: str, event_type: str) -> None:
            asyncio.run_coroutine_threadsafe(self._push_builds(), loop)

        build_queue.on_change = _on_change
        build_queue.start()

    async def _push_builds(self) -> None:
        self._store.set("current_builds", get_active_builds())
        self._store.set("previous_builds", get_finished_builds())

    # -- Broadcasting ------------------------------------------------------

    def _on_store_change(self, field_name: str, value: Any, prev: Any) -> None:
        del prev
        asyncio.run_coroutine_threadsafe(
            self._broadcast_state(field_name, value), self._loop
        )

    async def _send_state(
        self,
        ws: ServerConnection,
        session_id: str,
        field_name: str,
        data: Any,
    ) -> None:
        await self._send_message(
            ws,
            {
                "type": "state",
                "sessionId": session_id,
                "key": self._store.wire_key(field_name),
                "data": data,
            },
        )

    async def _send_message(
        self,
        ws: ServerConnection,
        payload: dict[str, Any],
    ) -> None:
        self._log_websocket_event(
            "send",
            session_id=payload.get("sessionId"),
            type=payload.get("type"),
            action=payload.get("action"),
            request_id=payload.get("requestId"),
            ok=payload.get("ok"),
            key=payload.get("key"),
            step=payload.get("step"),
            success=payload.get("success"),
            last_id=payload.get("last_id"),
            log_count=(
                len(payload["logs"]) if isinstance(payload.get("logs"), list) else None
            ),
        )
        await ws.send(json.dumps(payload))

    async def _open_layout(self, request: OpenLayoutRequest) -> Path:
        from atopile.layout_server.models import WsMessage
        from atopile.server.domains.layout import layout_service

        layout_path = resolve_layout_path(request)
        await asyncio.to_thread(layout_service.load, layout_path)
        await layout_service.start_watcher()
        model = await asyncio.to_thread(layout_service.manager.get_render_model)
        await layout_service.broadcast(WsMessage(type="layout_updated", model=model))
        return layout_path

    async def _broadcast_state(self, field_name: str, data: Any) -> None:
        wire_key = self._store.wire_key(field_name)
        dead: list[ServerConnection] = []
        for ws, sessions in list(self._subscriptions.items()):
            for session_id, keys in sessions.items():
                try:
                    if wire_key in keys:
                        await self._send_state(ws, session_id, field_name, data)
                except websockets.ConnectionClosed:
                    dead.append(ws)
                    break
        for ws in dead:
            self._clients.discard(ws)
            self._subscriptions.pop(ws, None)
            for task in self._log_tasks.pop(ws, {}).values():
                task.cancel()

    async def broadcast_state(self, field_name: str, data: Any) -> None:
        self._store.set(field_name, data)

    def _session_id(self, msg: dict[str, Any]) -> str:
        session_id = msg.get("sessionId")
        if isinstance(session_id, str) and session_id:
            return session_id
        return EXTENSION_SESSION_ID
