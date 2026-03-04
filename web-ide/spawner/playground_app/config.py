from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = BASE_DIR / "config.toml"


class ServerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    host: str
    port: int = Field(ge=1, le=65535)
    cookie_name: str
    cookie_max_age_seconds: int = Field(ge=60)
    cleanup_interval_seconds: int = Field(ge=5)
    pool_check_interval_seconds: int = Field(ge=5)
    max_idle_seconds: int = Field(ge=60)
    max_lifetime_seconds: int = Field(ge=60)
    revalidate_seconds: int = Field(ge=5)
    auto_build_frontend: bool


class PoolConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy: Literal["absolute", "relative"]
    target_n: int
    max_machine_count: int | None = Field(ge=1)

    @field_validator("target_n")
    @classmethod
    def validate_target(cls, value: int, info) -> int:
        strategy = info.data.get("strategy", "relative")
        if strategy == "absolute" and value < 0:
            raise ValueError("target_n must be >= 0 for absolute strategy")
        if strategy == "relative" and not (0 <= value <= 99):
            raise ValueError("target_n must be in [0, 99] for relative strategy")
        return value


class SpawnerHttpServiceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    internal_port: int = Field(ge=1, le=65535)
    force_https: bool
    auto_stop_machines: str
    auto_start_machines: bool
    min_machines_running: int = Field(ge=0)


class SpawnerVmConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cpu_kind: str
    cpus: int = Field(ge=1)
    memory_mb: int = Field(ge=64)


class SpawnerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    app: str
    primary_region: str
    dockerfile: str
    http_service: SpawnerHttpServiceConfig
    vm: SpawnerVmConfig


class WsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    class MachineVmConfig(BaseModel):
        model_config = ConfigDict(extra="forbid")

        cpu_kind: str
        cpus: int = Field(ge=1)
        memory_mb: int = Field(ge=128)

    class MachineRestartConfig(BaseModel):
        model_config = ConfigDict(extra="forbid")

        policy: str
        max_retries: int = Field(ge=0)

    class MachineConfig(BaseModel):
        model_config = ConfigDict(extra="forbid")

        vm: "WsConfig.MachineVmConfig"
        restart: "WsConfig.MachineRestartConfig"

    app: str
    region: str
    image: str
    machines_api: str
    machine: MachineConfig
    machine_wait_timeout_seconds: int = Field(ge=1)
    machine_wait_retries: int = Field(ge=1)
    dockerfile: str
    image_label: str
    deploy_strategy: str
    deploy_ha: bool


class InfraConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    spawner: SpawnerConfig
    ws: WsConfig


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    server: ServerConfig
    pool: PoolConfig
    infra: InfraConfig


def load_config(path: Path) -> AppConfig:
    with path.open("rb") as f:
        raw = tomllib.load(f)
    return AppConfig.model_validate(raw)
