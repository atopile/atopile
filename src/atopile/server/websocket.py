"""WebSocket connection management and action dispatch for the core server."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

import websockets
from websockets.asyncio.server import ServerConnection

from atopile.dataclasses import BuildRequest
from atopile.model import artifacts, packages, parts_search, stdlib
from atopile.model.build_queue import BuildQueue, _build_queue
from atopile.model.builds import (
    get_active_builds,
    get_finished_builds,
    handle_start_build,
)
from atopile.model.files import FileWatcher
from atopile.model.module_introspection import introspect_module_definition
from atopile.model.projects import handle_get_modules, handle_get_projects
from atopile.model.sqlite import Logs

log = logging.getLogger(__name__)

STREAM_POLL_INTERVAL = 0.25  # seconds


class CoreSocket:
    """Manages WebSocket connections and dispatches actions."""

    def __init__(self) -> None:
        self._clients: set[ServerConnection] = set()
        self._log_tasks: dict[ServerConnection, asyncio.Task] = {}
        self.bind_build_queue(_build_queue)

    # -- Client lifecycle --------------------------------------------------

    async def handle_client(self, ws: ServerConnection) -> None:
        self._clients.add(ws)
        log.info("Core WS client connected (%d total)", len(self._clients))

        try:
            # Send history on connect; active builds will arrive via on_change callbacks
            current = get_active_builds()
            previous = get_finished_builds()
            await ws.send(
                json.dumps({"type": "state", "key": "currentBuilds", "data": current})
            )
            await ws.send(
                json.dumps({"type": "state", "key": "previousBuilds", "data": previous})
            )

            async for raw in ws:
                msg = json.loads(raw)
                if msg.get("type") == "action":
                    await self._dispatch(ws, msg)

        except websockets.ConnectionClosed:
            pass
        finally:
            self._clients.discard(ws)
            task = self._log_tasks.pop(ws, None)
            if task:
                task.cancel()
            log.info("Core WS client disconnected (%d total)", len(self._clients))

    # -- Action dispatch ---------------------------------------------------

    async def _dispatch(self, ws: ServerConnection, msg: dict) -> None:
        match msg.get("action"):
            case "discoverProjects":
                paths = [Path(p) for p in msg.get("paths", []) if p]
                result = handle_get_projects(paths)
                await self.broadcast_state(
                    "projects", [p.model_dump() for p in result.projects]
                )

            case "listFiles":
                project_root = msg.get("projectRoot", "")
                result = FileWatcher.scan_and_serialize(project_root)
                await self.broadcast_state("projectFiles", result)
                FileWatcher.start(
                    project_root, self.broadcast_state, asyncio.get_running_loop()
                )

            case "startBuild":
                request = BuildRequest(
                    project_root=msg.get("projectRoot", ""),
                    targets=msg.get("targets", []),
                )
                try:
                    handle_start_build(request)
                except ValueError as e:
                    log.warning("startBuild failed: %s", e)

            case "getPackagesSummary":
                project_root = msg.get("projectRoot", "")
                root = Path(project_root) if project_root else None
                result = await asyncio.to_thread(packages.handle_packages_summary, root)
                await self.broadcast_state("packagesSummary", result.model_dump())

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
                await self.broadcast_state("packagesSummary", result.model_dump())

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
                await self.broadcast_state("packagesSummary", result.model_dump())

            case "getStdlib":
                type_filter = msg.get("typeFilter")
                search = msg.get("search")
                result = await asyncio.to_thread(
                    stdlib.handle_get_stdlib, type_filter, search
                )
                await self.broadcast_state("stdlibData", result.model_dump())

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
                await self.broadcast_state("structureData", data)

            case "searchParts":
                query = msg.get("query", "")
                limit = msg.get("limit", 50)
                parts, error = await asyncio.to_thread(
                    parts_search.handle_search_parts,
                    query,
                    limit=limit,
                )
                await self.broadcast_state(
                    "partsSearch", {"parts": parts, "error": error}
                )

            case "getInstalledParts":
                project_root = msg.get("projectRoot", "")
                parts = await asyncio.to_thread(
                    parts_search.handle_list_installed_parts,
                    project_root,
                )
                await self.broadcast_state("installedParts", {"parts": parts})

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
                await self.broadcast_state("installedParts", {"parts": parts})

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
                await self.broadcast_state("installedParts", {"parts": parts})

            case "getVariables":
                project_root = msg.get("projectRoot", "")
                target = msg.get("target", "default")
                data = await asyncio.to_thread(
                    artifacts.handle_get_variables,
                    project_root,
                    target,
                )
                await self.broadcast_state("variablesData", data or {"nodes": []})

            case "getBom":
                project_root = msg.get("projectRoot", "")
                target = msg.get("target", "default")
                data = await asyncio.to_thread(
                    artifacts.handle_get_bom,
                    project_root,
                    target,
                )
                await self.broadcast_state(
                    "bomData",
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
                build_id = msg.get("build_id", "").strip()
                if not build_id:
                    await ws.send(
                        json.dumps(
                            {"type": "logs_error", "error": "build_id is required"}
                        )
                    )
                    return
                old_task = self._log_tasks.pop(ws, None)
                if old_task:
                    old_task.cancel()
                query = {
                    "build_id": build_id,
                    "stage": msg.get("stage"),
                    "log_levels": msg.get("log_levels"),
                    "audience": msg.get("audience"),
                    "count": msg.get("count", 1000),
                }
                task = asyncio.create_task(self._log_stream_loop(ws, query))
                self._log_tasks[ws] = task
                log.debug("Log client subscribed to build %s", build_id)

            case "unsubscribeLogs":
                old_task = self._log_tasks.pop(ws, None)
                if old_task:
                    old_task.cancel()
                log.debug("Log client unsubscribed")

            case action:
                await ws.send(
                    json.dumps(
                        {
                            "type": "action_result",
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
            await ws.send(
                json.dumps(
                    {
                        "type": "logs_stream",
                        "logs": logs,
                        "last_id": new_last_id,
                    }
                )
            )
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
        await self.broadcast_state("currentBuilds", get_active_builds())
        await self.broadcast_state("previousBuilds", get_finished_builds())

    # -- Broadcasting ------------------------------------------------------

    async def broadcast_state(self, key: str, data: Any) -> None:
        msg = json.dumps({"type": "state", "key": key, "data": data})
        dead: list[ServerConnection] = []
        for ws in list(self._clients):
            try:
                await ws.send(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._clients.discard(ws)
