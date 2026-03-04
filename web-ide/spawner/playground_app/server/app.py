from __future__ import annotations

import asyncio
import time
from collections import deque
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse

from playground_app.config import AppConfig
from playground_app.models import (
    DashboardPoint,
    DashboardSeriesResponse,
    ErrorResponse,
    HealthResponse,
    SessionInfo,
)
from playground_app.server.fly_machines import FlyMachinesClient
from playground_app.server.pool import CAPACITY_ERROR_MESSAGE, CapacityError, PoolManager
from playground_app.session import SessionSigner

HISTORY_POINTS_MAX = 720


class AppRuntime:
    def __init__(self, cfg: AppConfig, machines: FlyMachinesClient, signer: SessionSigner):
        self.cfg = cfg
        self.machines = machines
        self.signer = signer
        self.sessions: dict[str, SessionInfo] = {}
        self.pool_ids: set[str] = set()
        self.pool = PoolManager(cfg=cfg, machines=machines, pool_ids=self.pool_ids)
        self.metrics_history: deque[DashboardPoint] = deque(maxlen=HISTORY_POINTS_MAX)
        self.metrics_interval_seconds = max(5, min(cfg.server.pool_check_interval_seconds, 30))
        self.start_time = time.time()
        self._tasks: list[asyncio.Task] = []

    async def cleanup_once(self) -> None:
        machines = await self.machines.list_machines()
        now = int(time.time() * 1000)
        live_ids: set[str] = set()

        for machine in machines:
            metadata = (machine.config or {}).get("metadata", {})
            if metadata.get("playground") != "true":
                continue
            live_ids.add(machine.id)
            if machine.id in self.pool_ids:
                continue

            session = self.sessions.get(machine.id)
            created = (
                session.created
                if session
                else _parse_machine_created_ms(machine.created_at, now)
                if machine.created_at
                else now
            )
            last_seen = session.last_seen if session else created
            idle_ms = now - last_seen
            age_ms = now - created

            if (
                idle_ms > self.cfg.server.max_idle_seconds * 1000
                or age_ms > self.cfg.server.max_lifetime_seconds * 1000
            ):
                self.sessions.pop(machine.id, None)
                if machine.state == "started":
                    await self.machines.stop_machine(machine.id)
                else:
                    await self.machines.destroy_machine(machine.id)

        for session_id in list(self.sessions):
            if session_id not in live_ids:
                self.sessions.pop(session_id, None)

    async def _run_cleanup_loop(self) -> None:
        while True:
            try:
                await self.cleanup_once()
            except Exception as exc:
                print(f"Cleanup error: {exc}")
            await asyncio.sleep(self.cfg.server.cleanup_interval_seconds)

    async def _run_pool_loop(self) -> None:
        while True:
            try:
                await self.pool.replenish_pool()
            except CapacityError as exc:
                print(f"Pool replenish error [{exc.code}]: {exc}")
            except Exception as exc:
                print(f"Pool replenish error: {exc}")
            await asyncio.sleep(self.cfg.server.pool_check_interval_seconds)

    async def capture_metrics_sample(self, fail_closed: bool = True) -> DashboardPoint:
        snapshot = await self.pool.snapshot(fail_closed=fail_closed)
        point = DashboardPoint(
            timestamp_ms=int(time.time() * 1000),
            active=snapshot.active_count,
            warm=snapshot.warm_count,
            total=snapshot.total_count,
        )
        self.metrics_history.append(point)
        return point

    def history_for_window(self, window_seconds: int) -> list[DashboardPoint]:
        if not self.metrics_history:
            return []
        cutoff_ms = int(time.time() * 1000) - window_seconds * 1000
        return [point for point in self.metrics_history if point.timestamp_ms >= cutoff_ms]

    async def _run_metrics_loop(self) -> None:
        while True:
            try:
                await self.capture_metrics_sample(fail_closed=True)
            except CapacityError as exc:
                print(f"Metrics sample error [{exc.code}]: {exc}")
            except Exception as exc:
                print(f"Metrics sample error: {exc}")
            await asyncio.sleep(self.metrics_interval_seconds)

    async def start(self) -> None:
        self._tasks = [
            asyncio.create_task(self._run_pool_loop()),
            asyncio.create_task(self._run_cleanup_loop()),
            asyncio.create_task(self._run_metrics_loop()),
        ]

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)


def _landing_html() -> str:
    return (Path(__file__).resolve().parents[1] / "templates" / "landing.html").read_text(encoding="utf-8")


def _dashboard_html() -> str:
    return (Path(__file__).resolve().parents[1] / "templates" / "dashboard.html").read_text(encoding="utf-8")


def _parse_machine_created_ms(raw: str, fallback_ms: int) -> int:
    try:
        # Fly API timestamps are ISO-8601; normalize trailing Z to UTC offset.
        normalized = raw.replace("Z", "+00:00")
        return int(datetime.fromisoformat(normalized).timestamp() * 1000)
    except Exception:
        return fallback_ms


def create_app(
    cfg: AppConfig,
    *,
    fly_token: str,
    start_background_tasks: bool = True,
    machines_client: FlyMachinesClient | None = None,
) -> FastAPI:
    token = fly_token.strip()
    if not token:
        raise ValueError("fly_token must be non-empty")
    machines = machines_client or FlyMachinesClient(cfg, token)
    signer = SessionSigner(
        cookie_name=cfg.server.cookie_name,
        max_age_seconds=cfg.server.cookie_max_age_seconds,
        fly_api_token=token,
    )

    runtime = AppRuntime(cfg=cfg, machines=machines, signer=signer)

    app = FastAPI(title="atopile playground spawner")

    @app.on_event("startup")
    async def startup() -> None:
        if start_background_tasks:
            await runtime.start()

    @app.on_event("shutdown")
    async def shutdown() -> None:
        if start_background_tasks:
            await runtime.stop()

    @app.get("/api/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(
            ok=True,
            sessions=len(runtime.sessions),
            pool=len(runtime.pool_ids),
            max_machine_count=cfg.pool.max_machine_count,
            uptime=int(time.time() - runtime.start_time),
        )

    @app.get("/api/dashboard/series", response_model=DashboardSeriesResponse)
    async def dashboard_series(window_seconds: int = 3600) -> DashboardSeriesResponse:
        window_seconds = max(60, min(window_seconds, 86400))

        try:
            if not runtime.metrics_history:
                await runtime.capture_metrics_sample(fail_closed=True)
        except CapacityError as exc:
            raise HTTPException(
                status_code=503,
                detail="Workspace control plane unavailable. Please retry.",
            ) from exc

        points = runtime.history_for_window(window_seconds)
        if not points:
            try:
                points = [await runtime.capture_metrics_sample(fail_closed=True)]
            except CapacityError as exc:
                raise HTTPException(
                    status_code=503,
                    detail="Workspace control plane unavailable. Please retry.",
                ) from exc

        latest = points[-1]
        return DashboardSeriesResponse(
            points=points,
            active=latest.active,
            warm=latest.warm,
            total=latest.total,
            max_machine_count=cfg.pool.max_machine_count,
        )

    def _clear_session(machine_id: str) -> Response:
        runtime.sessions.pop(machine_id, None)
        response = RedirectResponse(url="/", status_code=302)
        runtime.signer.clear_session_cookie(response)
        return response

    @app.post("/api/spawn", responses={503: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
    async def spawn() -> Response:
        try:
            machine = await runtime.pool.claim_machine()
            replay_state = FlyMachinesClient.extract_replay_state(machine)
            if not replay_state:
                raise RuntimeError(f"Machine {machine.id} missing replay state")

            machine_id = machine.id
            now_ms = int(time.time() * 1000)
            runtime.sessions[machine_id] = SessionInfo(
                created=now_ms,
                last_seen=now_ms,
                replay_state=replay_state,
            )
            response = RedirectResponse(url="/", status_code=302)
            runtime.signer.set_session_cookie(response, machine_id)
            asyncio.create_task(runtime.pool.replenish_pool())
            return response
        except CapacityError as exc:
            if exc.code == "CAPACITY_EXHAUSTED":
                error_message = CAPACITY_ERROR_MESSAGE
            else:
                error_message = "Workspace control plane unavailable. Please retry."
            return JSONResponse(
                status_code=503,
                content=ErrorResponse(error=error_message).model_dump(),
            )
        except Exception:
            return JSONResponse(
                status_code=500,
                content=ErrorResponse(error="Failed to create workspace. Please try again.").model_dump(),
            )

    @app.api_route("/favicon.png", methods=["GET", "HEAD"])
    @app.api_route("/favicon.svg", methods=["GET", "HEAD"])
    @app.api_route("/favicon.ico", methods=["GET", "HEAD"])
    async def favicon() -> Response:
        icon_path = Path(__file__).resolve().parents[1] / "static" / "favicon.png"
        if not icon_path.exists():
            return Response(status_code=404)
        return FileResponse(
            icon_path,
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=300"},
        )

    @app.get("/static/landing.js")
    async def landing_js() -> Response:
        js_path = Path(__file__).resolve().parents[1] / "static" / "landing.js"
        if not js_path.exists():
            return Response(status_code=404)
        return FileResponse(js_path, media_type="application/javascript")

    @app.get("/static/dashboard.js")
    async def dashboard_js() -> Response:
        js_path = Path(__file__).resolve().parents[1] / "static" / "dashboard.js"
        if not js_path.exists():
            return Response(status_code=404)
        return FileResponse(js_path, media_type="application/javascript")

    @app.get("/dashboard")
    async def dashboard() -> Response:
        return HTMLResponse(_dashboard_html())

    @app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
    async def route_all(request: Request, full_path: str) -> Response:
        no_launch = request.query_params.get("nolaunch") == "1"
        if no_launch and (full_path == "" or full_path == "/"):
            # Force launcher rendering even with an existing session cookie.
            return HTMLResponse(_landing_html())

        signed = request.cookies.get(cfg.server.cookie_name)
        machine_id = runtime.signer.verify(signed)
        if machine_id:
            session = runtime.sessions.get(machine_id)
            now_ms = int(time.time() * 1000)
            machine = None
            needs_validation = session is None or now_ms - session.last_validated > cfg.server.revalidate_seconds * 1000
            if needs_validation:
                machine = await runtime.machines.get_machine(machine_id)
                if machine and machine.state == "started":
                    replay_state = FlyMachinesClient.extract_replay_state(machine)
                    if not replay_state:
                        return _clear_session(machine_id)
                    if session is None:
                        session = SessionInfo(
                            created=now_ms,
                            last_seen=now_ms,
                            last_validated=now_ms,
                            replay_state=replay_state,
                        )
                        runtime.sessions[machine_id] = session
                    else:
                        session.last_validated = now_ms
                        session.replay_state = replay_state
                else:
                    return _clear_session(machine_id)

            session = runtime.sessions.get(machine_id)
            if session is None:
                return _clear_session(machine_id)
            if not session.replay_state:
                machine = machine or await runtime.machines.get_machine(machine_id)
                replay_state = FlyMachinesClient.extract_replay_state(machine)
                if not replay_state:
                    return _clear_session(machine_id)
                session.replay_state = replay_state

            session.last_seen = now_ms
            fallback_html = (
                "<!doctype html><html><head><meta charset='utf-8'>"
                "<title>Routing workspace…</title>"
                "<style>body{font-family:system-ui,sans-serif;background:#0c1118;color:#dde6f0;"
                "padding:2rem;line-height:1.5}code{background:#131b24;padding:.1rem .35rem;border-radius:4px}"
                "a{color:#f95015}</style></head><body>"
                "<h1>Routing to workspace</h1>"
                "<p>If this page does not switch automatically, replay routing is not active for this request.</p>"
                "<p>Open the spawner through its Fly hostname (not localhost) to enable replay routing.</p>"
                f"<p>Session machine: <code>{machine_id}</code></p>"
                "</body></html>"
            )
            return HTMLResponse(
                content=fallback_html,
                status_code=200,
                headers={"fly-replay": (f"app={cfg.infra.ws.app};instance={machine_id};state={session.replay_state}")},
            )

        if full_path == "" or full_path == "/":
            return HTMLResponse(_landing_html())

        return RedirectResponse(url="/", status_code=302)

    return app
