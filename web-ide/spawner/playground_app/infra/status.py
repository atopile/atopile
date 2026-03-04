from __future__ import annotations

import json
import shutil
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib import error, request

from rich.console import Console
from rich.table import Table

from playground_app.config import AppConfig


def _run(
    cmd: list[str],
    cwd: Path | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=check,
        text=True,
        capture_output=True,
    )


def _resolve_fly() -> str:
    for candidate in ("fly", "flyctl"):
        if shutil.which(candidate):
            return candidate
    raise RuntimeError("flyctl not found. Install flyctl and ensure it is in PATH.")


def _machines_list(fly: str, app: str) -> list[dict[str, Any]]:
    out = _run([fly, "machines", "list", "--app", app, "--json"]).stdout
    data = json.loads(out)
    return data if isinstance(data, list) else []


def _first_string(row: dict[str, Any], *keys: str, default: str = "-") -> str:
    for key in keys:
        value = row.get(key)
        if isinstance(value, str) and value:
            return value
    return default


def _format_relative_time(timestamp: str | None) -> str:
    if not timestamp:
        return "-"
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        delta = datetime.now(UTC) - dt.astimezone(UTC)
    except Exception:
        return timestamp
    seconds = int(delta.total_seconds())
    if seconds < 0:
        return "just now"
    if seconds < 60:
        return f"{seconds}s ago"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    return f"{days}d ago"


@dataclass
class MachineRow:
    app: str
    machine_id: str
    name: str
    state: str
    region: str
    created_at: str
    image: str
    private_ip: str


@dataclass
class SpawnerHealth:
    sessions: int
    pool: int
    max_machine_count: int | None


def _normalize_machine(app: str, row: dict[str, Any]) -> MachineRow:
    config = row.get("config")
    image = "-"
    if isinstance(config, dict):
        config_image = config.get("image")
        if isinstance(config_image, str) and config_image:
            image = config_image

    return MachineRow(
        app=app,
        machine_id=_first_string(row, "id", "ID"),
        name=_first_string(row, "name", "Name"),
        state=_first_string(row, "state", "State"),
        region=_first_string(row, "region", "Region"),
        created_at=_first_string(row, "created_at", "CreatedAt", default=""),
        image=image,
        private_ip=_first_string(row, "private_ip", "PrivateIP"),
    )


def _state_style(state: str) -> str:
    state_l = state.lower()
    if state_l in {"started", "running"}:
        return "green"
    if state_l in {"stopped", "created"}:
        return "yellow"
    if state_l in {"destroyed", "failed"}:
        return "red"
    return "white"


def _image_short(image: str) -> str:
    if image == "-":
        return image
    if ":" in image:
        return image.rsplit(":", 1)[-1]
    return image


def _health_url(cfg: AppConfig, local: bool) -> str:
    if local:
        return f"http://127.0.0.1:{cfg.server.port}/api/health"
    return f"https://{cfg.infra.spawner.app}.fly.dev/api/health"


def _fetch_spawner_health(url: str, timeout_seconds: float = 3.0) -> SpawnerHealth:
    try:
        with request.urlopen(url, timeout=timeout_seconds) as resp:
            if resp.getcode() != 200:
                raise RuntimeError(f"source-of-truth health check failed: {url} returned {resp.getcode()}")
            raw = resp.read().decode("utf-8")
    except (TimeoutError, OSError, error.URLError) as exc:
        raise RuntimeError(f"source-of-truth health check failed: {url}: {exc}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"source-of-truth health check returned invalid JSON: {url}") from exc

    if not isinstance(data, dict):
        raise RuntimeError(f"source-of-truth health check returned invalid body: {url}")
    if data.get("ok") is not True:
        raise RuntimeError(f"source-of-truth health check reports not-ok: {url}")

    sessions = data.get("sessions")
    pool = data.get("pool")
    max_machine_count = data.get("max_machine_count")
    if not isinstance(sessions, int):
        raise RuntimeError(f"source-of-truth health check missing integer 'sessions': {url}")
    if not isinstance(pool, int):
        raise RuntimeError(f"source-of-truth health check missing integer 'pool': {url}")
    if max_machine_count is not None and not isinstance(max_machine_count, int):
        raise RuntimeError(f"source-of-truth health check missing integer-or-null 'max_machine_count': {url}")

    return SpawnerHealth(
        sessions=sessions,
        pool=pool,
        max_machine_count=max_machine_count,
    )


def status(cfg: AppConfig, *, local: bool = False) -> None:
    fly = _resolve_fly()
    _run([fly, "auth", "whoami"])
    health_url = _health_url(cfg, local)
    spawner_health = _fetch_spawner_health(health_url)

    rows: list[MachineRow] = []
    apps = [cfg.infra.spawner.app, cfg.infra.ws.app]
    for app in apps:
        for raw_machine in _machines_list(fly, app):
            rows.append(_normalize_machine(app, raw_machine))

    rows.sort(key=lambda row: (row.app, row.state, row.machine_id))

    summary: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        summary[row.app][row.state] += 1
        summary[row.app]["total"] += 1

    console = Console()
    console.print("[bold]Playground Infrastructure Status[/bold]")
    console.print(f"Spawner app: [cyan]{cfg.infra.spawner.app}[/cyan]")
    console.print(f"Workspace app: [cyan]{cfg.infra.ws.app}[/cyan]")
    console.print(f"Health source: [cyan]{health_url}[/cyan]")
    console.print()

    summary_table = Table(title="Machine Summary", show_header=True)
    summary_table.add_column("App")
    summary_table.add_column("Total", justify="right")
    summary_table.add_column("Started", justify="right")
    summary_table.add_column("Stopped", justify="right")
    summary_table.add_column("Other", justify="right")
    summary_table.add_column("Active", justify="right")
    summary_table.add_column("Warm", justify="right")
    summary_table.add_column("Max", justify="right")

    active_text = str(spawner_health.sessions)
    warm_text = str(spawner_health.pool)
    max_text = str(spawner_health.max_machine_count) if spawner_health.max_machine_count is not None else "∞"

    for app in apps:
        counter = summary[app]
        total = counter.get("total", 0)
        started = counter.get("started", 0) + counter.get("running", 0)
        stopped = counter.get("stopped", 0) + counter.get("created", 0)
        other = max(0, total - started - stopped)
        pool_active = active_text if app == cfg.infra.ws.app else "-"
        pool_warm = warm_text if app == cfg.infra.ws.app else "-"
        pool_max = max_text if app == cfg.infra.ws.app else "-"
        summary_table.add_row(
            app,
            str(total),
            str(started),
            str(stopped),
            str(other),
            pool_active,
            pool_warm,
            pool_max,
        )

    console.print(summary_table)
    console.print()

    details = Table(title="Machines", show_header=True)
    details.add_column("App", style="cyan")
    details.add_column("Machine ID")
    details.add_column("Name")
    details.add_column("State")
    details.add_column("Region")
    details.add_column("Created")
    details.add_column("IP")
    details.add_column("Image")

    if not rows:
        details.add_row("-", "-", "-", "-", "-", "-", "-", "-")
    else:
        for row in rows:
            details.add_row(
                row.app,
                row.machine_id,
                row.name,
                f"[{_state_style(row.state)}]{row.state}[/]",
                row.region,
                _format_relative_time(row.created_at),
                row.private_ip,
                _image_short(row.image),
            )

    console.print(details)
