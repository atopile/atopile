from __future__ import annotations

import pytest

from atopile.server.routes import parts_search as parts_routes


class _FakeServerState:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def emit_event(self, event_type: str, payload: dict) -> None:
        self.events.append((event_type, payload))


@pytest.mark.anyio
async def test_install_part_route_supports_create_package(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    server_state = _FakeServerState()

    def fake_install_part_as_package(lcsc_id: str, project_root: str) -> dict:
        captured["lcsc_id"] = lcsc_id
        captured["project_root"] = project_root
        return {
            "identifier": "local/raspberry-pi-rp2040",
            "path": (
                f"{project_root}/packages/Raspberry_Pi_RP2040/Raspberry_Pi_RP2040.ato"
            ),
            "created_package": True,
            "import_statement": (
                'from "local/raspberry-pi-rp2040/Raspberry_Pi_RP2040.ato" '
                "import Raspberry_Pi_RP2040"
            ),
        }

    monkeypatch.setattr(
        parts_routes.parts_domain,
        "handle_install_part_as_package",
        fake_install_part_as_package,
    )
    monkeypatch.setattr(parts_routes, "get_server_state", lambda: server_state)

    response = await parts_routes.install_part(
        parts_routes.InstallPartRequest(
            lcsc_id="C2040",
            project_root="/tmp/project",
            create_package=True,
        )
    )

    assert response.success is True
    assert response.created_package is True
    assert response.identifier == "local/raspberry-pi-rp2040"
    assert response.import_statement
    assert captured == {"lcsc_id": "C2040", "project_root": "/tmp/project"}
    assert server_state.events == [
        (
            "parts_changed",
            {
                "project_root": "/tmp/project",
                "lcsc_id": "C2040",
                "installed": False,
                "created_package": True,
            },
        )
    ]
