from __future__ import annotations

from pathlib import Path

from atopile.model import parts_search


def test_install_part_as_package_creates_wrapper(
    monkeypatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    package_root = project_root / "packages" / "Raspberry_Pi_RP2040"
    package_root.mkdir(parents=True)
    wrapper_path = package_root / "Raspberry_Pi_RP2040.ato"

    monkeypatch.setattr(
        parts_search,
        "handle_get_install_identifier",
        lambda lcsc_id, project_root=None: {
            "identifier": "Raspberry_Pi_RP2040",
            "entry_module": "Raspberry_Pi_RP2040",
        },
    )
    monkeypatch.setattr(
        "atopile.model.projects.create_local_package",
        lambda project_root, name, entry_module, description=None: {
            "path": str(package_root),
            "module_path": str(wrapper_path),
            "identifier": "local/raspberry-pi-rp2040",
            "import_statement": (
                'from "local/raspberry-pi-rp2040/Raspberry_Pi_RP2040.ato" '
                "import Raspberry_Pi_RP2040"
            ),
        },
    )
    monkeypatch.setattr(
        parts_search,
        "handle_install_part",
        lambda lcsc_id, package_root: {
            "identifier": "Raspberry_Pi_RP2040",
            "path": f"{package_root}/parts/Raspberry_Pi_RP2040",
        },
    )

    response = parts_search.handle_install_part_as_package(
        "C2040",
        str(project_root),
    )

    assert response["created_package"] is True
    assert response["identifier"] == "local/raspberry-pi-rp2040"
    assert response["import_statement"] == (
        'from "local/raspberry-pi-rp2040/Raspberry_Pi_RP2040.ato" '
        "import Raspberry_Pi_RP2040"
    )
    assert wrapper_path.read_text(encoding="utf-8") == (
        'from "parts/Raspberry_Pi_RP2040/Raspberry_Pi_RP2040.ato" import '
        "Raspberry_Pi_RP2040_package\n\n"
        "module Raspberry_Pi_RP2040:\n"
        "    package = new Raspberry_Pi_RP2040_package\n"
    )
