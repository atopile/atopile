from __future__ import annotations

import copy
from pathlib import Path

import pytest

from playground_app.config import AppConfig, load_config


def _base_config_dict() -> dict:
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
            "auto_build_frontend": True,
        },
        "pool": {
            "strategy": "relative",
            "target_n": 50,
            "max_machine_count": 5,
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


def test_load_config_from_file(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[server]
host = "0.0.0.0"
port = 9090
cookie_name = "session"
cookie_max_age_seconds = 3600
cleanup_interval_seconds = 300
pool_check_interval_seconds = 30
max_idle_seconds = 1800
max_lifetime_seconds = 3600
revalidate_seconds = 60
auto_build_frontend = true

[pool]
strategy = "absolute"
target_n = 2
max_machine_count = 5

[infra.spawner]
app = "atopile-playground"
primary_region = "sjc"
dockerfile = "Dockerfile"

[infra.spawner.http_service]
internal_port = 8080
force_https = true
auto_stop_machines = "off"
auto_start_machines = true
min_machines_running = 1

[infra.spawner.vm]
cpu_kind = "shared"
cpus = 1
memory_mb = 256

[infra.ws]
app = "my-ws"
region = "sjc"
image = "registry.fly.io/atopile-ws:latest"
machines_api = "https://api.machines.dev"
machine_wait_timeout_seconds = 60
machine_wait_retries = 3
dockerfile = "../Dockerfile"
image_label = "latest"
deploy_strategy = "immediate"
deploy_ha = false

[infra.ws.machine.vm]
cpu_kind = "performance"
cpus = 1
memory_mb = 2048

[infra.ws.machine.restart]
policy = "on-failure"
max_retries = 3
""",
        encoding="utf-8",
    )

    cfg = load_config(config_path)
    assert cfg.server.port == 9090
    assert cfg.pool.strategy == "absolute"
    assert cfg.pool.target_n == 2
    assert cfg.infra.ws.app == "my-ws"


def test_relative_target_rejects_100() -> None:
    raw = copy.deepcopy(_base_config_dict())
    raw["pool"]["strategy"] = "relative"
    raw["pool"]["target_n"] = 100

    with pytest.raises(ValueError):
        AppConfig.model_validate(raw)


def test_ws_machine_service_rejected_in_config() -> None:
    raw = copy.deepcopy(_base_config_dict())
    raw["infra"]["ws"]["machine"]["service"] = {"internal_port": 3080}

    with pytest.raises(ValueError):
        AppConfig.model_validate(raw)
