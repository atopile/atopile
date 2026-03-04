from __future__ import annotations

import asyncio
import copy
import time
from typing import Any

import pytest
from fastapi.testclient import TestClient

from playground_app.config import AppConfig
from playground_app.server.app import create_app


class FakeMachines:
    def __init__(self, started: list[dict[str, Any]] | None = None):
        self.started: dict[str, dict[str, Any]] = {}
        for machine in started or []:
            config = machine.setdefault("config", {})
            metadata = config.setdefault("metadata", {})
            metadata.setdefault("playground", "true")
            env = config.setdefault("env", {})
            env.setdefault("PLAYGROUND_REPLAY_STATE", f"state-{machine['id']}")
            self.started[machine["id"]] = machine
        self.counter = 0

    async def create_machine(self):
        self.counter += 1
        machine_id = f"m{self.counter}"
        machine = {
            "id": machine_id,
            "state": "started",
            "config": {
                "metadata": {"playground": "true"},
                "env": {"PLAYGROUND_REPLAY_STATE": f"state-{machine_id}"},
            },
        }
        self.started[machine_id] = machine
        return type("Machine", (), machine)

    async def wait_for_machine(self, machine_id: str) -> None:
        _ = machine_id

    async def list_machines(self, fail_on_error: bool = False):
        _ = fail_on_error
        return [type("Machine", (), m) for m in self.started.values()]

    async def get_machine(self, machine_id: str):
        machine = self.started.get(machine_id)
        if not machine:
            return None
        return type("Machine", (), machine)

    async def destroy_machine(self, machine_id: str) -> None:
        self.started.pop(machine_id, None)

    async def stop_machine(self, machine_id: str) -> None:
        self.started.pop(machine_id, None)


def _base_config_dict() -> dict[str, Any]:
    return {
        "server": {
            "host": "0.0.0.0",
            "port": 8080,
            "cookie_name": "session",
            "cookie_max_age_seconds": 3600,
            "cleanup_interval_seconds": 300,
            "pool_check_interval_seconds": 30,
            "max_idle_seconds": 1800,
            "max_lifetime_seconds": 3600,
            "revalidate_seconds": 60,
            "auto_build_frontend": False,
        },
        "pool": {
            "strategy": "absolute",
            "target_n": 0,
            "max_machine_count": 1,
        },
        "infra": {
            "spawner": {
                "app": "atopile-playground",
                "primary_region": "sjc",
                "dockerfile": "Dockerfile",
                "http_service": {
                    "internal_port": 8080,
                    "force_https": True,
                    "auto_stop_machines": "off",
                    "auto_start_machines": True,
                    "min_machines_running": 1,
                },
                "vm": {
                    "cpu_kind": "shared",
                    "cpus": 1,
                    "memory_mb": 256,
                },
            },
            "ws": {
                "app": "atopile-ws",
                "region": "sjc",
                "image": "registry.fly.io/atopile-ws:latest",
                "machines_api": "https://api.machines.dev",
                "machine_wait_timeout_seconds": 60,
                "machine_wait_retries": 3,
                "dockerfile": "../Dockerfile",
                "image_label": "latest",
                "deploy_strategy": "immediate",
                "deploy_ha": False,
                "machine": {
                    "vm": {
                        "cpu_kind": "performance",
                        "cpus": 1,
                        "memory_mb": 2048,
                    },
                    "restart": {
                        "policy": "on-failure",
                        "max_retries": 3,
                    },
                },
            },
        },
    }


def _cfg(*, max_machine_count: int = 1, target_n: int = 0) -> AppConfig:
    raw = copy.deepcopy(_base_config_dict())
    raw["pool"]["max_machine_count"] = max_machine_count
    raw["pool"]["target_n"] = target_n
    return AppConfig.model_validate(raw)


def test_create_app_requires_runtime_token() -> None:
    with pytest.raises(ValueError, match="fly_token must be non-empty"):
        create_app(_cfg(), start_background_tasks=False, fly_token="")


def test_spawn_capacity_exhausted_message() -> None:
    cfg = _cfg(max_machine_count=1)
    fake = FakeMachines(
        started=[
            {
                "id": "active-1",
                "state": "started",
                "config": {"metadata": {"playground": "true"}},
            }
        ]
    )
    app = create_app(cfg, start_background_tasks=False, machines_client=fake, fly_token="token")
    with TestClient(app) as client:
        res = client.post("/api/spawn")
    assert res.status_code == 503
    assert res.json()["error"] == "No free machines available. Try later or install locally"


def test_spawn_and_replay_header() -> None:
    cfg = _cfg(max_machine_count=10)
    fake = FakeMachines()
    app = create_app(cfg, start_background_tasks=False, machines_client=fake, fly_token="token")
    with TestClient(app) as client:
        spawn_res = client.post("/api/spawn", follow_redirects=False)
        assert spawn_res.status_code == 302
        replay_res = client.get("/some/path")

    assert replay_res.status_code == 200
    assert replay_res.headers["fly-replay"].startswith("app=atopile-ws;instance=")
    assert ";state=state-m1" in replay_res.headers["fly-replay"]


def test_spawn_fails_if_machine_missing_replay_state() -> None:
    fake = FakeMachines()

    async def create_machine_without_state():
        machine = await FakeMachines.create_machine(fake)
        machine.config["env"] = {}
        return machine

    fake.create_machine = create_machine_without_state  # type: ignore[method-assign]
    app = create_app(_cfg(), start_background_tasks=False, machines_client=fake, fly_token="token")
    with TestClient(app) as client:
        res = client.post("/api/spawn")
    assert res.status_code == 500
    assert res.json()["error"] == "Failed to create workspace. Please try again."


def test_nolaunch_forces_launcher_even_with_session_cookie() -> None:
    cfg = _cfg(max_machine_count=10)
    fake = FakeMachines()
    app = create_app(cfg, start_background_tasks=False, machines_client=fake, fly_token="token")
    with TestClient(app) as client:
        spawn_res = client.post("/api/spawn", follow_redirects=False)
        assert spawn_res.status_code == 302
        launch_res = client.get("/?nolaunch=1")

    assert launch_res.status_code == 200
    assert "fly-replay" not in launch_res.headers
    assert "atopile playground" in launch_res.text


def test_favicon_uses_atopile_logo_asset() -> None:
    app = create_app(_cfg(), start_background_tasks=False, fly_token="token")
    with TestClient(app) as client:
        res = client.get("/favicon.ico")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("image/png")
    assert len(res.content) > 0


def test_dashboard_page_and_series_api() -> None:
    cfg = _cfg(max_machine_count=10)
    fake = FakeMachines(
        started=[
            {
                "id": "active-1",
                "state": "started",
                "config": {"metadata": {"playground": "true"}},
            }
        ]
    )
    app = create_app(cfg, start_background_tasks=False, machines_client=fake, fly_token="token")
    with TestClient(app) as client:
        dashboard_res = client.get("/dashboard")
        series_res = client.get("/api/dashboard/series?window_seconds=3600")

    assert dashboard_res.status_code == 200
    assert "dashboard.js" in dashboard_res.text

    assert series_res.status_code == 200
    body = series_res.json()
    assert body["active"] == 1
    assert body["warm"] == 0
    assert body["total"] == 1
    assert body["max_machine_count"] == 10
    assert len(body["points"]) >= 1


def test_startup_does_not_block_on_pool_replenish() -> None:
    cfg = _cfg(max_machine_count=10, target_n=1)

    class SlowMachines(FakeMachines):
        async def list_machines(self, fail_on_error: bool = False):
            _ = fail_on_error
            await asyncio.sleep(2)
            return []

    app = create_app(cfg, machines_client=SlowMachines(), fly_token="token")
    started = time.perf_counter()
    with TestClient(app) as client:
        res = client.get("/api/health")
        assert res.status_code == 200
        body = res.json()
        assert body["max_machine_count"] == 10
    assert time.perf_counter() - started < 1
