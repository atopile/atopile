from __future__ import annotations

import base64
import secrets
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel

from playground_app.config import AppConfig


class FlyMachine(BaseModel):
    id: str
    state: str | None = None
    created_at: str | None = None
    config: dict[str, Any] | None = None


class MachinesApiError(RuntimeError):
    pass


REPLAY_STATE_ENV = "PLAYGROUND_REPLAY_STATE"
WORKSPACE_INTERNAL_PORT = 3080


def _load_caddyfile() -> str:
    caddy_path = Path(__file__).resolve().parents[2] / "Caddyfile"
    if not caddy_path.is_file():
        raise RuntimeError("Caddyfile missing at playground/Caddyfile; required for workspace machine config")
    return caddy_path.read_text(encoding="utf-8")


class FlyMachinesClient:
    def __init__(self, cfg: AppConfig, token: str):
        self.cfg = cfg
        self.token = token
        self._caddyfile = _load_caddyfile() + (
            f"\n# Plain HTTP for Fly proxy (internal_port={WORKSPACE_INTERNAL_PORT})\n"
            f"http://:{WORKSPACE_INTERNAL_PORT} {{\n\timport atopile_proxy\n}}\n"
        )

    async def _request(
        self,
        method: str,
        path: str,
        payload: Any = None,
    ) -> tuple[int, Any]:
        url = f"{self.cfg.infra.ws.machines_api}{path}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.request(method, url, headers=headers, json=payload)
        data: Any
        try:
            data = resp.json()
        except Exception:
            data = resp.text
        return resp.status_code, data

    @staticmethod
    def extract_replay_state(machine: FlyMachine | None) -> str | None:
        if machine is None:
            return None
        env = (machine.config or {}).get("env", {})
        if not isinstance(env, dict):
            return None
        value = env.get(REPLAY_STATE_ENV)
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    def _machine_config(self, replay_state: str) -> dict[str, Any]:
        machine_cfg = self.cfg.infra.ws.machine
        return {
            "image": self.cfg.infra.ws.image,
            "auto_destroy": True,
            "guest": {
                "cpu_kind": machine_cfg.vm.cpu_kind,
                "cpus": machine_cfg.vm.cpus,
                "memory_mb": machine_cfg.vm.memory_mb,
            },
            "env": {
                REPLAY_STATE_ENV: replay_state,
            },
            "files": [
                {
                    "guest_path": "/home/openvscode-server/.local/etc/Caddyfile",
                    "raw_value": base64.b64encode(self._caddyfile.encode("utf-8")).decode("utf-8"),
                }
            ],
            "services": [
                {
                    "protocol": "tcp",
                    "internal_port": WORKSPACE_INTERNAL_PORT,
                    "ports": [
                        {"port": 443, "handlers": ["tls", "http"], "force_https": False},
                        {"port": 80, "handlers": ["http"], "force_https": True},
                    ],
                    "concurrency": {
                        "type": "connections",
                        "soft_limit": 25,
                        "hard_limit": 30,
                    },
                    "autostart": True,
                    "autostop": "off",
                }
            ],
            "restart": {
                "policy": machine_cfg.restart.policy,
                "max_retries": machine_cfg.restart.max_retries,
            },
            "metadata": {"playground": "true"},
        }

    async def create_machine(self) -> FlyMachine:
        replay_state = secrets.token_hex(16)
        status, data = await self._request(
            "POST",
            f"/v1/apps/{self.cfg.infra.ws.app}/machines",
            {
                "region": self.cfg.infra.ws.region,
                "config": self._machine_config(replay_state),
            },
        )
        if status != 200:
            raise MachinesApiError(f"Machines API create failed ({status}): {data}")
        return FlyMachine.model_validate(data)

    async def wait_for_machine(self, machine_id: str) -> None:
        for _ in range(self.cfg.infra.ws.machine_wait_retries):
            status, data = await self._request(
                "GET",
                (
                    f"/v1/apps/{self.cfg.infra.ws.app}/machines/{machine_id}"
                    f"/wait?state=started&timeout={self.cfg.infra.ws.machine_wait_timeout_seconds}"
                ),
            )
            if status == 200:
                return
            if status == 408:
                continue
            raise MachinesApiError(f"Machine wait failed ({status}): {data}")
        raise MachinesApiError("Machine failed to start within timeout")

    async def list_machines(self, fail_on_error: bool = False) -> list[FlyMachine]:
        status, data = await self._request(
            "GET",
            f"/v1/apps/{self.cfg.infra.ws.app}/machines",
        )
        if status != 200:
            if fail_on_error:
                raise MachinesApiError(f"Machines API list failed ({status}): {data}")
            return []
        if not isinstance(data, list):
            return []
        return [FlyMachine.model_validate(item) for item in data]

    async def get_machine(self, machine_id: str) -> FlyMachine | None:
        status, data = await self._request(
            "GET",
            f"/v1/apps/{self.cfg.infra.ws.app}/machines/{machine_id}",
        )
        if status != 200:
            return None
        return FlyMachine.model_validate(data)

    async def destroy_machine(self, machine_id: str) -> None:
        await self._request(
            "DELETE",
            f"/v1/apps/{self.cfg.infra.ws.app}/machines/{machine_id}?force=true",
        )

    async def stop_machine(self, machine_id: str) -> None:
        await self._request(
            "POST",
            f"/v1/apps/{self.cfg.infra.ws.app}/machines/{machine_id}/stop",
        )
