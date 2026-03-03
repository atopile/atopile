"""Closed-loop frontend drag regression test (ESP32 fixture + Puppeteer)."""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import pytest

ROOT_DIR = Path(__file__).resolve().parents[2]
ESP32_PCB = (
    ROOT_DIR / "examples/esp32_minimal/layouts/esp32_minimal/esp32_minimal.kicad_pcb"
)
PUPPETEER_SCRIPT = ROOT_DIR / "test/layout_server/frontend_drag_closed_loop.mjs"
FRONTEND_DIR = ROOT_DIR / "src/atopile/layout_server/frontend"


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        return int(sock.getsockname()[1])


def _wait_for_server(base_url: str, timeout_s: float = 60.0) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with urlopen(f"{base_url}/api/render-model", timeout=1.5) as resp:
                if resp.status == 200:
                    return
        except URLError:
            time.sleep(0.2)
            continue
    raise TimeoutError(f"Layout server did not become ready within {timeout_s:.1f}s")


def _launch_layout_server(port: int, pcb_path: Path) -> subprocess.Popen[str]:
    server_code = (
        "import os;"
        "from pathlib import Path;"
        "import uvicorn;"
        "from atopile.layout_server.__main__ import create_app;"
        "app = create_app(Path(os.environ['PCB_PATH']));"
        "uvicorn.run("
        "app, host='127.0.0.1', port=int(os.environ['PORT']), log_level='error'"
        ")"
    )
    env = os.environ.copy()
    env["PORT"] = str(port)
    env["PCB_PATH"] = str(pcb_path)
    return subprocess.Popen(
        [sys.executable, "-c", server_code],
        cwd=str(ROOT_DIR),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _extract_json_line(stdout: str) -> dict:
    for line in reversed(stdout.splitlines()):
        candidate = line.strip()
        if candidate.startswith("{") and candidate.endswith("}"):
            return json.loads(candidate)
    raise ValueError(f"Could not find JSON object in script output:\n{stdout}")


@pytest.mark.regression
def test_frontend_drag_closed_loop_esp32():
    if shutil.which("node") is None:
        pytest.skip("node is required for closed-loop frontend regression test")
    if not ESP32_PCB.is_file():
        pytest.skip(f"ESP32 fixture PCB not found: {ESP32_PCB}")
    if not (FRONTEND_DIR / "node_modules/puppeteer").exists():
        pytest.skip(
            "puppeteer is not installed (run npm install in layout_server/frontend)"
        )
    if not PUPPETEER_SCRIPT.is_file():
        pytest.skip(f"Puppeteer script missing: {PUPPETEER_SCRIPT}")

    port = _find_free_port()
    base_url = f"http://127.0.0.1:{port}"
    server = _launch_layout_server(port, ESP32_PCB)

    try:
        _wait_for_server(base_url)
        run = subprocess.run(
            ["node", str(PUPPETEER_SCRIPT), "--url", base_url],
            cwd=str(ROOT_DIR),
            check=True,
            capture_output=True,
            text=True,
            timeout=240,
        )
        result = _extract_json_line(run.stdout)
    finally:
        server.terminate()
        try:
            server.wait(timeout=8)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=8)

    debug = json.dumps(result, indent=2, sort_keys=True)

    assert result["filters"]["padsToggleOk"], f"Could not toggle Pads filter\n{debug}"
    assert result["filters"]["padsRestoreOk"], f"Could not restore Pads filter\n{debug}"
    assert result["filters"]["zonesToggleOk"], f"Could not toggle Zones filter\n{debug}"
    assert result["filters"]["zonesRestoreOk"], (
        f"Could not restore Zones filter\n{debug}"
    )

    base_vertices = result["filters"]["baseVertices"]
    pads_off_vertices = result["filters"]["padsOffVertices"]
    pads_on_vertices = result["filters"]["padsOnVertices"]
    zones_off_vertices = result["filters"]["zonesOffVertices"]
    zones_on_vertices = result["filters"]["zonesOnVertices"]
    assert (
        base_vertices
        and pads_off_vertices
        and pads_on_vertices
        and zones_off_vertices
        and zones_on_vertices
    ), "Missing renderer layer vertex stats\n" + debug

    base_total = base_vertices["totalVertices"]
    pads_off_total = pads_off_vertices["totalVertices"]
    pads_on_total = pads_on_vertices["totalVertices"]
    zones_off_total = zones_off_vertices["totalVertices"]
    zones_on_total = zones_on_vertices["totalVertices"]

    assert pads_off_total < base_total, (
        f"Pads filter did not reduce rendered static vertices\n{debug}"
    )
    assert zones_off_total < base_total, (
        f"Zones filter did not reduce rendered static vertices\n{debug}"
    )
    assert abs(pads_on_total - base_total) <= max(2000, base_total * 0.01), (
        "Pads restore did not recover baseline rendered static vertices\n" + debug
    )
    assert abs(zones_on_total - base_total) <= max(2000, base_total * 0.01), (
        "Zones restore did not recover baseline rendered static vertices\n" + debug
    )

    assert result["zOrder"]["ok"], (
        f"Zone depth is not below copper depth: {result['zOrder']}\n{debug}"
    )

    assert result["drag"]["overlayBeforeRatio"] > 0.0001, (
        "Overlay text did not appear before drag; test scenario invalid\n" + debug
    )
    assert result["drag"]["overlayDuringRatio"] > 0.0001, (
        "Overlay text disappeared during drag\n" + debug
    )

    start_pos = result["drag"]["startPos"]
    expected_delta = result["drag"]["expectedDelta"]
    after_immediate = result["drag"]["posAfterImmediate"]
    after_settled = result["drag"]["posAfterSettled"]

    assert (
        start_pos is not None
        and expected_delta is not None
        and after_immediate is not None
    ), "Missing drag position samples\n" + debug
    moved_dx = after_immediate["x"] - start_pos["x"]
    moved_dy = after_immediate["y"] - start_pos["y"]
    expected_dx = expected_delta["dx"]
    expected_dy = expected_delta["dy"]
    assert abs(moved_dx - expected_dx) < 0.5 and abs(moved_dy - expected_dy) < 0.5, (
        "Dragged footprint did not remain at drop position immediately on mouseup\n"
        + debug
    )

    assert after_settled is not None, f"Missing settled drag position sample\n{debug}"
    settled_dx = after_settled["x"] - after_immediate["x"]
    settled_dy = after_settled["y"] - after_immediate["y"]
    assert abs(settled_dx) < 0.05 and abs(settled_dy) < 0.05, (
        "Dragged footprint moved again after mouseup (possible snap-back/update jump)\n"
        + debug
    )

    assert result["timings"]["downMs"] < 1000, (
        f"Drag-start latency is too high on ESP32 fixture\n{debug}"
    )
