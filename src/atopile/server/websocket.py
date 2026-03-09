"""WebSocket connection management and action dispatch for the core server."""

# TODO: Replace raw websocket action payload decoding with typed request models.

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlparse
from urllib.request import urlopen

import websockets
from websockets.asyncio.server import ServerConnection

from atopile.dataclasses import (
    BuildRequest,
    PackageDetails,
    PackagesSummaryData,
    PackageSummaryItem,
    Project,
    UiBuildLogRequest,
    UiInstalledPartsData,
    UiLogEntry,
    UiLogsErrorMessage,
    UiLogsStreamMessage,
    UiMigrationState,
    UiMigrationStep,
    UiMigrationStepResult,
    UiMigrationTopic,
    UiPackageDetailState,
    UiPartDetail,
    UiPartsSearchData,
    UiSidebarDetails,
)
from atopile.model import artifacts, migrations, packages, parts_search, stdlib
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


def _asset_proxy_allowed_hosts() -> set[str]:
    allowed = set(
        host.strip()
        for host in os.getenv("ATOPILE_PACKAGES_ASSET_HOSTS", "").split(",")
        if host.strip()
    )
    if allowed:
        return allowed
    return {
        "cloudfront.net",
        "s3.amazonaws.com",
        "s3.us-east-1.amazonaws.com",
        "s3.us-west-2.amazonaws.com",
        "atopileapi.com",
    }


def _is_host_allowed(host: str) -> bool:
    allowed = _asset_proxy_allowed_hosts()
    if not allowed:
        return os.getenv("ATOPILE_ALLOW_UNSAFE_ASSET_PROXY", "").lower() in {
            "1",
            "true",
            "yes",
        }
    return host in allowed or any(
        host.endswith(f".{allowed_host}") for allowed_host in allowed
    )


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

    def _sidebar_details(self) -> dict[str, Any]:
        return cast(dict[str, Any], self._store.dump("sidebar_details"))

    def _sidebar_details_state(self) -> UiSidebarDetails:
        return cast(UiSidebarDetails, self._store.get("sidebar_details"))

    def _clear_sidebar_details(self) -> None:
        self._store.set("sidebar_details", UiSidebarDetails())

    def _find_project(self, project_root: str | None) -> Project | None:
        if not project_root:
            return None
        projects = cast(list[Project], self._store.get("projects"))
        return next(
            (project for project in projects if project.root == project_root), None
        )

    def _find_package_summary(self, package_id: str) -> PackageSummaryItem:
        packages_summary = cast(
            PackagesSummaryData, self._store.get("packages_summary")
        )
        match = next(
            (pkg for pkg in packages_summary.packages if pkg.identifier == package_id),
            None,
        )
        if match:
            return match

        publisher, _, name = package_id.partition("/")
        summary = PackageSummaryItem(
            identifier=package_id,
            name=name or package_id,
            publisher=publisher or "unknown",
            installed=False,
        )
        return summary

    async def _set_package_details(
        self,
        project_root: str | None,
        package_id: str,
        *,
        loading: bool,
        error: str | None = None,
        action_error: str | None = None,
        details: PackageDetails | None = None,
    ) -> None:
        state = self._sidebar_details_state()
        self._store.set(
            "sidebar_details",
            state.model_copy(
                update={
                    "view": "package",
                    "package": UiPackageDetailState(
                        project_root=project_root,
                        package_id=package_id,
                        summary=self._find_package_summary(package_id),
                        details=details,
                        loading=loading,
                        error=error,
                        action_error=action_error,
                    ),
                }
            ),
        )

    async def _load_package_details(
        self,
        project_root: str | None,
        package_id: str,
        *,
        action_error: str | None = None,
    ) -> None:
        await self._set_package_details(
            project_root,
            package_id,
            loading=True,
            action_error=action_error,
        )
        try:
            details = await asyncio.to_thread(
                packages.handle_get_package_details,
                package_id,
                Path(project_root) if project_root else None,
                None,
            )
        except Exception as exc:
            await self._set_package_details(
                project_root,
                package_id,
                loading=False,
                error=str(exc),
                action_error=action_error,
            )
            return

        if details is None:
            await self._set_package_details(
                project_root,
                package_id,
                loading=False,
                error=f"No details found for {package_id}.",
                action_error=action_error,
            )
            return

        await self._set_package_details(
            project_root,
            package_id,
            loading=False,
            details=details,
            action_error=action_error,
        )

    async def _set_part_details(
        self,
        *,
        project_root: str | None,
        lcsc: str | None,
        part: UiPartDetail | None,
        loading: bool,
        error: str | None = None,
        action_error: str | None = None,
    ) -> None:
        state = self._sidebar_details_state()
        self._store.set(
            "sidebar_details",
            state.model_copy(
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
            ),
        )

    def _make_part_seed(
        self,
        *,
        project_root: str | None,
        identifier: str | None,
        lcsc: str | None,
        installed: bool,
    ) -> UiPartDetail:
        installed_parts = cast(UiInstalledPartsData, self._store.get("installed_parts"))
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

        search_state = cast(UiPartsSearchData, self._store.get("parts_search"))
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

    async def _load_part_details(
        self,
        *,
        project_root: str | None,
        lcsc: str | None,
        identifier: str | None = None,
        installed: bool = False,
        seed: UiPartDetail | None = None,
        action_error: str | None = None,
    ) -> None:
        base_part = seed or self._make_part_seed(
            project_root=project_root,
            identifier=identifier,
            lcsc=lcsc,
            installed=installed,
        )
        await self._set_part_details(
            project_root=project_root,
            lcsc=lcsc,
            part=base_part,
            loading=bool(lcsc),
            action_error=action_error,
        )
        if not lcsc:
            await self._set_part_details(
                project_root=project_root,
                lcsc=lcsc,
                part=base_part,
                loading=False,
                error="This part does not have an LCSC identifier.",
                action_error=action_error,
            )
            return

        try:
            detail = await asyncio.to_thread(parts_search.handle_get_part_details, lcsc)
        except Exception as exc:
            await self._set_part_details(
                project_root=project_root,
                lcsc=lcsc,
                part=base_part,
                loading=False,
                error=str(exc),
                action_error=action_error,
            )
            return

        if detail is None:
            await self._set_part_details(
                project_root=project_root,
                lcsc=lcsc,
                part=base_part,
                loading=False,
                error=f"No details found for {lcsc}.",
                action_error=action_error,
            )
            return

        merged = detail.model_copy(
            update={
                "identifier": base_part.identifier
                or detail.identifier
                or detail.mpn
                or lcsc
                or "",
                "lcsc": detail.lcsc or lcsc,
                "path": detail.path or base_part.path,
                "installed": installed,
            }
        )
        await self._set_part_details(
            project_root=project_root,
            lcsc=lcsc,
            part=merged,
            loading=False,
            action_error=action_error,
        )

    async def _set_migration_details(self, migration: UiMigrationState) -> None:
        state = self._sidebar_details_state()
        self._store.set(
            "sidebar_details",
            state.model_copy(
                update={
                    "view": "migration",
                    "migration": migration,
                }
            ),
        )

    async def _load_migration_details(self, project_root: str) -> None:
        project = self._find_project(project_root)
        project_name = project.name if project else Path(project_root).name
        needs_migration = bool(project and project.needs_migration)
        await self._set_migration_details(
            UiMigrationState(
                project_root=project_root,
                project_name=project_name,
                needs_migration=needs_migration,
                loading=True,
            )
        )
        try:
            steps = [
                UiMigrationStep.model_validate(step.to_dict())
                for step in migrations.get_all_steps()
            ]
            topics = [
                UiMigrationTopic.model_validate(topic)
                for topic in migrations.get_topics()
            ]
        except Exception as exc:
            await self._set_migration_details(
                UiMigrationState(
                    project_root=project_root,
                    project_name=project_name,
                    needs_migration=needs_migration,
                    loading=False,
                    error=str(exc),
                )
            )
            return

        await self._set_migration_details(
            UiMigrationState(
                project_root=project_root,
                project_name=project_name,
                needs_migration=needs_migration,
                steps=steps,
                topics=topics,
                step_results=[UiMigrationStepResult(step_id=step.id) for step in steps],
                loading=False,
            )
        )

    async def _update_migration_project_state(self, project_root: str) -> None:
        migration_state = self._sidebar_details_state().migration
        project = self._find_project(project_root)
        await self._set_migration_details(
            migration_state.model_copy(
                update={
                    "project_root": project_root,
                    "project_name": project.name
                    if project
                    else Path(project_root).name,
                    "needs_migration": bool(project and project.needs_migration),
                    "loading": False,
                }
            ),
        )

    async def _refresh_project_entry(self, project_root: str) -> None:
        projects = cast(list[Project], self._store.get("projects"))
        refreshed = await asyncio.to_thread(handle_get_projects, [Path(project_root)])
        replacement = next(iter(refreshed.projects), None)
        if replacement is None:
            return
        next_projects = [
            replacement if project.root == project_root else project
            for project in projects
        ]
        self._store.set("projects", next_projects)

    async def _proxy_remote_asset(
        self, url: str, filename: str | None
    ) -> dict[str, str]:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Invalid asset URL")
        if not _is_host_allowed(parsed.netloc):
            raise ValueError("Asset host not allowed")

        def _fetch() -> dict[str, str]:
            with urlopen(url, timeout=30) as response:
                content_type = (
                    response.headers.get_content_type() or "application/octet-stream"
                )
                data = response.read()
            return {
                "contentType": content_type,
                "filename": filename or Path(parsed.path).name or "asset",
                "data": base64.b64encode(data).decode("ascii"),
            }

        return await asyncio.to_thread(_fetch)

    # -- Action dispatch ---------------------------------------------------

    async def _dispatch(self, ws: ServerConnection, msg: dict) -> None:
        session_id = self._session_id(msg)
        action = str(msg.get("action", ""))
        request_id = msg.get("requestId")
        if not isinstance(request_id, str):
            request_id = None
        if self._vscode_bridge.handles(action):
            await self._vscode_bridge.forward_request(ws, session_id, msg)
            return

        match msg.get("action"):
            case "getRemoteAsset":
                try:
                    result = await self._proxy_remote_asset(
                        str(msg.get("url", "")),
                        str(msg.get("filename")) if msg.get("filename") else None,
                    )
                    await self._send_action_result(
                        ws,
                        session_id,
                        action,
                        request_id,
                        result=result,
                    )
                except Exception as exc:
                    await self._send_action_result(
                        ws,
                        session_id,
                        action,
                        request_id,
                        error=str(exc),
                    )

            case "getPartDetails":
                try:
                    lcsc_id = str(msg.get("lcsc", ""))
                    result = await asyncio.to_thread(
                        parts_search.handle_get_part_details,
                        lcsc_id,
                    )
                    await self._send_action_result(
                        ws,
                        session_id,
                        action,
                        request_id,
                        result={
                            "part": None
                            if result is None
                            else result.model_dump(mode="json", by_alias=True)
                        },
                        error=None if result else f"Part not found: {lcsc_id}",
                    )
                except Exception as exc:
                    await self._send_action_result(
                        ws,
                        session_id,
                        action,
                        request_id,
                        error=str(exc),
                    )

            case "getMigrationSteps":
                try:
                    await self._send_action_result(
                        ws,
                        session_id,
                        action,
                        request_id,
                        result={
                            "steps": [
                                step.to_dict() for step in migrations.get_all_steps()
                            ],
                            "topics": migrations.get_topics(),
                        },
                    )
                except Exception as exc:
                    await self._send_action_result(
                        ws,
                        session_id,
                        action,
                        request_id,
                        error=str(exc),
                    )

            case "getPartModelData":
                try:
                    lcsc_id = str(msg.get("lcsc", ""))
                    result = await asyncio.to_thread(
                        parts_search.handle_get_part_model,
                        lcsc_id,
                    )
                    if not result:
                        raise ValueError(f"3D model not found: {lcsc_id}")
                    data, name = result
                    await self._send_action_result(
                        ws,
                        session_id,
                        action,
                        request_id,
                        result={
                            "contentType": "model/step",
                            "filename": name,
                            "data": base64.b64encode(data).decode("ascii"),
                        },
                    )
                except Exception as exc:
                    await self._send_action_result(
                        ws,
                        session_id,
                        action,
                        request_id,
                        error=str(exc),
                    )

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

            case "showPackageDetails":
                await self._load_package_details(
                    msg.get("projectRoot") or None,
                    str(msg.get("packageId", "")),
                )

            case "closeSidebarDetails":
                self._clear_sidebar_details()

            case "installPackage":
                project_root = Path(msg.get("projectRoot", ""))
                pkg_id = msg.get("packageId", "")
                version = msg.get("version")
                action_error = None
                try:
                    await asyncio.to_thread(
                        packages.install_package_to_project,
                        project_root,
                        pkg_id,
                        version,
                    )
                except Exception as e:
                    log.warning("installPackage failed: %s", e)
                    action_error = str(e)
                result = await asyncio.to_thread(
                    packages.handle_packages_summary, project_root
                )
                self._store.set("packages_summary", result)
                current = self._sidebar_details_state()
                package_state = current.package
                if (
                    current.view == "package"
                    and package_state.package_id == pkg_id
                    and package_state.project_root == str(project_root)
                ):
                    await self._load_package_details(
                        str(project_root),
                        str(pkg_id),
                        action_error=action_error,
                    )

            case "removePackage":
                project_root = Path(msg.get("projectRoot", ""))
                pkg_id = msg.get("packageId", "")
                action_error = None
                try:
                    await asyncio.to_thread(
                        packages.remove_package_from_project,
                        project_root,
                        pkg_id,
                    )
                except Exception as e:
                    log.warning("removePackage failed: %s", e)
                    action_error = str(e)
                result = await asyncio.to_thread(
                    packages.handle_packages_summary, project_root
                )
                self._store.set("packages_summary", result)
                current = self._sidebar_details_state()
                package_state = current.package
                if (
                    current.view == "package"
                    and package_state.package_id == pkg_id
                    and package_state.project_root == str(project_root)
                ):
                    await self._load_package_details(
                        str(project_root),
                        str(pkg_id),
                        action_error=action_error,
                    )

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

            case "showPartDetails":
                await self._load_part_details(
                    project_root=msg.get("projectRoot") or None,
                    identifier=msg.get("identifier"),
                    lcsc=msg.get("lcsc"),
                    installed=bool(msg.get("installed")),
                )

            case "installPart":
                project_root = msg.get("projectRoot", "")
                lcsc = msg.get("lcsc", "")
                action_error = None
                try:
                    await asyncio.to_thread(
                        parts_search.handle_install_part,
                        lcsc,
                        project_root,
                    )
                except Exception as e:
                    log.warning("installPart failed: %s", e)
                    action_error = str(e)
                parts = await asyncio.to_thread(
                    parts_search.handle_list_installed_parts,
                    project_root,
                )
                self._store.set("installed_parts", {"parts": parts})
                current = self._sidebar_details_state()
                part_state = current.part
                if (
                    current.view == "part"
                    and part_state.lcsc == lcsc
                    and part_state.project_root == project_root
                ):
                    part = part_state.part
                    await self._load_part_details(
                        project_root=project_root,
                        identifier=part.identifier if part else None,
                        lcsc=lcsc,
                        installed=True,
                        seed=part.model_copy(update={"installed": True})
                        if part
                        else None,
                        action_error=action_error,
                    )
                await self._send_action_result(
                    ws,
                    session_id,
                    action,
                    request_id,
                    result={"success": action_error is None},
                    error=action_error,
                )

            case "uninstallPart":
                project_root = msg.get("projectRoot", "")
                lcsc = msg.get("lcsc", "")
                action_error = None
                try:
                    await asyncio.to_thread(
                        parts_search.handle_uninstall_part,
                        lcsc,
                        project_root,
                    )
                except Exception as e:
                    log.warning("uninstallPart failed: %s", e)
                    action_error = str(e)
                parts = await asyncio.to_thread(
                    parts_search.handle_list_installed_parts,
                    project_root,
                )
                self._store.set("installed_parts", {"parts": parts})
                current = self._sidebar_details_state()
                part_state = current.part
                if (
                    current.view == "part"
                    and part_state.lcsc == lcsc
                    and part_state.project_root == project_root
                ):
                    part = part_state.part
                    await self._load_part_details(
                        project_root=project_root,
                        identifier=part.identifier if part else None,
                        lcsc=lcsc,
                        installed=False,
                        seed=part.model_copy(update={"installed": False})
                        if part
                        else None,
                        action_error=action_error,
                    )
                await self._send_action_result(
                    ws,
                    session_id,
                    action,
                    request_id,
                    result={"success": action_error is None},
                    error=action_error,
                )

            case "showMigrationDetails":
                project_root = str(msg.get("projectRoot", ""))
                if project_root:
                    await self._load_migration_details(project_root)

            case "runMigration" | "migrateProjectSteps":
                project_root = str(msg.get("projectRoot", ""))
                selected_steps = [str(step) for step in msg.get("steps", []) if step]
                if not project_root:
                    return
                migration_state = self._sidebar_details_state().migration
                step_results = [
                    UiMigrationStepResult(
                        step_id=step.id,
                        status="running" if step.id in selected_steps else "idle",
                    )
                    for step in migration_state.steps
                ]
                await self._set_migration_details(
                    migration_state.model_copy(
                        update={
                            "step_results": step_results,
                            "loading": False,
                            "running": True,
                            "completed": False,
                            "error": None,
                        }
                    ),
                )
                for step_id in selected_steps:
                    try:
                        await migrations.get_step(step_id).run(Path(project_root))
                        status = "success"
                        error = None
                    except Exception as exc:
                        status = "error"
                        error = str(exc)

                    migration_state = self._sidebar_details_state().migration
                    next_results = [
                        UiMigrationStepResult(
                            step_id=result.step_id,
                            status=status,
                            error=error,
                        )
                        if result.step_id == step_id
                        else result
                        for result in migration_state.step_results
                    ]
                    await self._set_migration_details(
                        migration_state.model_copy(
                            update={
                                "step_results": next_results,
                                "loading": False,
                                "running": True,
                                "completed": False,
                                "error": None,
                            }
                        ),
                    )
                    await ws.send(
                        json.dumps(
                            {
                                "type": "migration_step_result",
                                "project_root": project_root,
                                "step": step_id,
                                "success": status == "success",
                                "error": error,
                            }
                        )
                    )
                migration_state = self._sidebar_details_state().migration
                has_errors = any(
                    result.status == "error" for result in migration_state.step_results
                )
                await self._set_migration_details(
                    migration_state.model_copy(
                        update={
                            "loading": False,
                            "running": False,
                            "completed": True,
                            "error": None
                            if not has_errors
                            else "Some migration steps failed.",
                        }
                    ),
                )
                await self._refresh_project_entry(project_root)
                await self._update_migration_project_state(project_root)
                await ws.send(
                    json.dumps(
                        {
                            "type": "migration_result",
                            "project_root": project_root,
                            "success": not has_errors,
                        }
                    )
                )
                await self._send_action_result(
                    ws,
                    session_id,
                    action,
                    request_id,
                    result={"success": not has_errors},
                    error=None if not has_errors else "Some migration steps failed.",
                )

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

    async def _send_action_result(
        self,
        ws: ServerConnection,
        session_id: str,
        action: str,
        request_id: str | None,
        *,
        result: Any = None,
        error: str | None = None,
    ) -> None:
        if not request_id:
            return
        await ws.send(
            json.dumps(
                {
                    "type": "action_result",
                    "sessionId": session_id,
                    "requestId": request_id,
                    "action": action,
                    "ok": error is None,
                    "result": result,
                    "error": error,
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
