from __future__ import annotations

from playground_app.config import AppConfig
from playground_app.infra.status import _health_url


def _cfg(*, port: int = 8080) -> AppConfig:
    return AppConfig.model_validate(
        {
            "server": {
                "host": "0.0.0.0",
                "port": port,
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
    )


def test_health_url_remote() -> None:
    cfg = _cfg()
    assert _health_url(cfg, local=False) == "https://atopile-playground.fly.dev/api/health"


def test_health_url_local() -> None:
    cfg = _cfg(port=9090)
    assert _health_url(cfg, local=True) == "http://127.0.0.1:9090/api/health"
