"""WebSocket connection management and action dispatch for the core server."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

import websockets
from websockets.asyncio.server import ServerConnection

from atopile.dataclasses import (
    BuildRequest,
    UiBuildLogRequest,
    UiLogEntry,
    UiLogsErrorMessage,
    UiLogsStreamMessage,
)
from atopile.model import artifacts, packages, parts_search, stdlib
from atopile.model.build_queue import BuildQueue, _build_queue
from atopile.model.builds import (
    get_active_builds,
    get_finished_builds,
    handle_start_build,
)
from atopile.model.file_watcher import FileWatcher
from atopile.model.module_introspection import introspect_module_definition
from atopile.model.projects import handle_get_modules, handle_get_projects
from atopile.model.sqlite import Logs
from atopile.server.domains.vscode_bridge import VscodeBridge
from atopile.server.store import Store

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
        log.info("Core WS client connected (%d total)", len(self._clients))

        try:
            async for raw in ws:
                msg = json.loads(raw)
                match msg.get("type"):
                    case "subscribe":
                        await self._handle_subscribe(ws, msg)
                    case "action":
                        await self._dispatch(ws, msg)
                    case "extension_response":
                        await self._vscode_bridge.handle_response(
                            ws, self._session_id(msg), msg
                        )

        except websockets.ConnectionClosed:
            pass
        finally:
            self._clients.discard(ws)
            self._subscriptions.pop(ws, None)
            self._vscode_bridge.remove_client(ws)
            for task in self._log_tasks.pop(ws, {}).values():
                task.cancel()
            log.info("Core WS client disconnected (%d total)", len(self._clients))

    async def _handle_subscribe(
        self, ws: ServerConnection, msg: dict[str, Any]
    ) -> None:
        session_id = self._session_id(msg)
        keys = {str(key) for key in msg.get("keys", [])}
        self._subscriptions.setdefault(ws, {})[session_id] = keys
        for key in keys:
            try:
                field_name = self._store.require_field_name(key)
                await self._send_state(
                    ws, session_id, field_name, self._store.dump(field_name)
                )
            except KeyError:
                log.warning("Client subscribed to unknown state key: %s", key)

    # -- Action dispatch ---------------------------------------------------

    async def _dispatch(self, ws: ServerConnection, msg: dict) -> None:
        session_id = self._session_id(msg)
        action = str(msg.get("action", ""))
        if self._vscode_bridge.handles(action):
            await self._vscode_bridge.forward_request(ws, session_id, msg)
            return

        match msg.get("action"):
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

            case "selectTarget":
                self._store.merge(
                    "project_state",
                    {
                        "selectedTarget": msg.get("target") or None,
                    },
                )

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

            case "coreStartupError":
                self._store.merge("core_status", {"error": msg.get("message")})

            case "extensionSettings":
                self._store.merge(
                    "extension_settings",
                    {
                        "devPath": msg.get("devPath", ""),
                        "autoInstall": msg.get("autoInstall", True),
                    },
                )

            case "updateExtensionSetting":
                key = msg.get("key")
                if isinstance(key, str):
                    self._store.merge("extension_settings", {key: msg.get("value")})

            case "setActiveFile":
                self._store.merge(
                    "project_state",
                    {
                        "activeFilePath": msg.get("filePath"),
                    },
                )

            case "discoverProjects":
                paths = [Path(p) for p in msg.get("paths", []) if p]
                result = handle_get_projects(paths)
                self._store.set("projects", result.projects)

            case "listFiles":
                project_root = msg.get("projectRoot", "")
                if project_root:
                    await self._project_files.watch([Path(project_root)])
                else:
                    self._store.set("project_files", [])

            case "startBuild":
                request = BuildRequest(
                    project_root=msg.get("projectRoot", ""),
                    targets=msg.get("targets", []),
                    include_targets=msg.get("includeTargets", []),
                    exclude_targets=msg.get("excludeTargets", []),
                )
                try:
                    handle_start_build(request)
                except ValueError as e:
                    log.warning("startBuild failed: %s", e)

            case "getPackagesSummary":
                project_root = msg.get("projectRoot", "")
                root = Path(project_root) if project_root else None
                result = await asyncio.to_thread(packages.handle_packages_summary, root)
                self._store.set("packages_summary", result)

            case "installPackage":
                project_root = Path(msg.get("projectRoot", ""))
                pkg_id = msg.get("packageId", "")
                version = msg.get("version")
                try:
                    await asyncio.to_thread(
                        packages.install_package_to_project,
                        project_root,
                        pkg_id,
                        version,
                    )
                except Exception as e:
                    log.warning("installPackage failed: %s", e)
                result = await asyncio.to_thread(
                    packages.handle_packages_summary, project_root
                )
                self._store.set("packages_summary", result)

            case "removePackage":
                project_root = Path(msg.get("projectRoot", ""))
                pkg_id = msg.get("packageId", "")
                try:
                    await asyncio.to_thread(
                        packages.remove_package_from_project,
                        project_root,
                        pkg_id,
                    )
                except Exception as e:
                    log.warning("removePackage failed: %s", e)
                result = await asyncio.to_thread(
                    packages.handle_packages_summary, project_root
                )
                self._store.set("packages_summary", result)

            case "getStdlib":
                type_filter = msg.get("typeFilter")
                search = msg.get("search")
                result = await asyncio.to_thread(
                    stdlib.handle_get_stdlib, type_filter, search
                )
                self._store.set("stdlib_data", result)

            case "getStructure":
                project_root = msg.get("projectRoot", "")
                type_filter = msg.get("typeFilter")
                modules_result = await asyncio.to_thread(
                    handle_get_modules, project_root, type_filter
                )
                if modules_result:
                    enriched = []
                    for mod in modules_result.modules:
                        try:
                            enriched_mod = await asyncio.to_thread(
                                introspect_module_definition,
                                Path(project_root),
                                mod,
                            )
                            enriched.append(enriched_mod)
                        except Exception:
                            enriched.append(mod)
                    data = {
                        "modules": [m.model_dump() for m in enriched],
                        "total": len(enriched),
                    }
                else:
                    data = {"modules": [], "total": 0}
                self._store.set("structure_data", data)

            case "searchParts":
                query = msg.get("query", "")
                limit = msg.get("limit", 50)
                parts, error = await asyncio.to_thread(
                    parts_search.handle_search_parts,
                    query,
                    limit=limit,
                )
                self._store.set("parts_search", {"parts": parts, "error": error})

            case "getInstalledParts":
                project_root = msg.get("projectRoot", "")
                parts = await asyncio.to_thread(
                    parts_search.handle_list_installed_parts,
                    project_root,
                )
                self._store.set("installed_parts", {"parts": parts})

            case "installPart":
                project_root = msg.get("projectRoot", "")
                lcsc = msg.get("lcsc", "")
                try:
                    await asyncio.to_thread(
                        parts_search.handle_install_part,
                        lcsc,
                        project_root,
                    )
                except Exception as e:
                    log.warning("installPart failed: %s", e)
                parts = await asyncio.to_thread(
                    parts_search.handle_list_installed_parts,
                    project_root,
                )
                self._store.set("installed_parts", {"parts": parts})

            case "uninstallPart":
                project_root = msg.get("projectRoot", "")
                lcsc = msg.get("lcsc", "")
                try:
                    await asyncio.to_thread(
                        parts_search.handle_uninstall_part,
                        lcsc,
                        project_root,
                    )
                except Exception as e:
                    log.warning("uninstallPart failed: %s", e)
                parts = await asyncio.to_thread(
                    parts_search.handle_list_installed_parts,
                    project_root,
                )
                self._store.set("installed_parts", {"parts": parts})

            case "getVariables":
                project_root = msg.get("projectRoot", "")
                target = msg.get("target", "default")
                data = await asyncio.to_thread(
                    artifacts.handle_get_variables,
                    project_root,
                    target,
                )
                self._store.set("variables_data", data or {"nodes": []})

            case "getBom":
                project_root = msg.get("projectRoot", "")
                target = msg.get("target", "default")
                data = await asyncio.to_thread(
                    artifacts.handle_get_bom,
                    project_root,
                    target,
                )
                self._store.set(
                    "bom_data",
                    data
                    or {
                        "components": [],
                        "totalQuantity": 0,
                        "uniqueParts": 0,
                        "estimatedCost": None,
                        "outOfStock": 0,
                    },
                )

            case "subscribeLogs":
                request = UiBuildLogRequest.model_validate(msg)
                build_id = request.build_id.strip()
                if not build_id:
                    payload = UiLogsErrorMessage(
                        error="buildId is required"
                    ).model_dump(mode="json")
                    payload["sessionId"] = session_id
                    await ws.send(json.dumps(payload))
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
                log.debug("Log client subscribed to build %s", build_id)

            case "unsubscribeLogs":
                old_task = self._log_tasks.setdefault(ws, {}).pop(session_id, None)
                if old_task:
                    old_task.cancel()
                log.debug("Log client unsubscribed")

            case action:
                await ws.send(
                    json.dumps(
                        {
                            "type": "action_result",
                            "sessionId": session_id,
                            "action": action,
                            "result": {
                                "success": False,
                                "message": f"Unknown action: {action}",
                            },
                        }
                    )
                )

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
        except Exception:
            log.exception("Log stream error")

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
            await ws.send(json.dumps(payload))
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
        await ws.send(
            json.dumps(
                {
                    "type": "state",
                    "sessionId": session_id,
                    "key": self._store.wire_key(field_name),
                    "data": data,
                }
            )
        )

    async def _broadcast_state(self, field_name: str, data: Any) -> None:
        wire_key = self._store.wire_key(field_name)
        dead: list[ServerConnection] = []
        for ws, sessions in list(self._subscriptions.items()):
            try:
                for session_id, keys in sessions.items():
                    if wire_key in keys:
                        await self._send_state(ws, session_id, field_name, data)
            except Exception:
                dead.append(ws)
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
