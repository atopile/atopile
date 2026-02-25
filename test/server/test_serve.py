"""Smoke tests: hub and core server start up and respond on their assigned ports."""

from __future__ import annotations

import asyncio
import json
import os
import select
import socket
import subprocess
import sys
import time

import requests
import websockets


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_hub_and_core_server_start_and_respond():
    """
    Start both servers the way the extension does (env vars),
    then verify a WS client can subscribe through the hub and
    get state relayed from the core server.
    """
    hub_port = _free_port()
    core_port = _free_port()
    env = {
        **os.environ,
        "ATOPILE_HUB_PORT": str(hub_port),
        "ATOPILE_CORE_SERVER_PORT": str(core_port),
    }

    # Start core server first (so the hub can connect to it)
    core_proc = subprocess.Popen(
        [sys.executable, "-m", "atopile", "serve", "core"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    hub_proc = subprocess.Popen(
        [sys.executable, "-m", "atopile", "serve", "hub"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    try:
        # Wait for both ready markers
        for name, proc, marker in [
            ("core", core_proc, "ATOPILE_SERVER_READY"),
            ("hub", hub_proc, "ATOPILE_HUB_READY"),
        ]:
            deadline = time.monotonic() + 15
            found = False
            while time.monotonic() < deadline:
                ready, _, _ = select.select([proc.stdout], [], [], 1.0)
                if not ready:
                    continue
                line = proc.stdout.readline().decode()
                if marker in line:
                    found = True
                    break
            assert found, f"{name} did not print {marker}"

        # Core server: HTTP health check
        resp = requests.get(f"http://127.0.0.1:{core_port}/health", timeout=5)
        assert resp.json()["status"] == "ok"

        # Hub: WS subscribe returns state
        async def _ws_check():
            # Give hub a moment to connect to core server
            await asyncio.sleep(1)
            async with websockets.connect(
                f"ws://localhost:{hub_port}/atopile-ui"
            ) as ws:
                await ws.send(json.dumps({"type": "subscribe"}))
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
                assert msg["type"] == "state"

        asyncio.run(_ws_check())
    finally:
        for proc in (hub_proc, core_proc):
            proc.terminate()
            proc.wait(timeout=5)
