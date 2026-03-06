from pathlib import Path

import yaml

from atopile.server.domains import projects as projects_domain


def test_discover_projects_includes_nested_package_targets(tmp_path: Path):
    project_root = tmp_path / "auto-picking"
    project_root.mkdir()
    (project_root / "ato.yaml").write_text(
        """
requires-atopile: ^0.14.0
builds:
  default:
    entry: main.ato:App
""".strip()
    )

    package_root = project_root / "packages" / "rp2040"
    package_root.mkdir(parents=True)
    (package_root / "ato.yaml").write_text(
        """
requires-atopile: ^0.14.0
builds:
  package:
    entry: rp2040.ato:RP2040
""".strip()
    )

    skipped_root = project_root / ".ato" / "modules" / "vendor" / "ignored"
    skipped_root.mkdir(parents=True)
    (skipped_root / "ato.yaml").write_text(
        """
requires-atopile: ^0.14.0
builds:
  hidden:
    entry: hidden.ato:Hidden
""".strip()
    )

    projects = projects_domain.discover_projects_in_paths([project_root])

    assert len(projects) == 1
    assert [target.name for target in projects[0].targets] == ["default", "package"]
    assert projects[0].targets[0].root == str(project_root)
    assert projects[0].targets[1].root == str(package_root)


def test_create_local_package_uses_layouts_directory(tmp_path: Path):
    project_root = tmp_path / "demo"
    project_root.mkdir()
    (project_root / "ato.yaml").write_text(
        """
requires-atopile: ^0.14.0
paths:
  src: ./
  layout: ./layouts
builds:
  default:
    entry: main.ato:App
""".strip()
    )

    package = projects_domain.create_local_package(project_root, "rp2040", "RP2040")

    package_root = Path(package["path"])
    package_ato = yaml.safe_load((package_root / "ato.yaml").read_text(encoding="utf-8"))

    assert (package_root / "layouts").is_dir()
    assert not (package_root / "elec").exists()
    assert package_ato["paths"]["layout"] == "./layouts"


def test_create_local_package_writes_file_dependency_identifier(tmp_path: Path):
    project_root = tmp_path / "demo"
    project_root.mkdir()
    (project_root / "ato.yaml").write_text(
        """
requires-atopile: ^0.14.0
paths:
  src: ./
  layout: ./layouts
builds:
  default:
    entry: main.ato:App
""".strip()
    )

    projects_domain.create_local_package(project_root, "Raspberry_Pi_RP2040", "RP2040")

    project_ato = yaml.safe_load((project_root / "ato.yaml").read_text(encoding="utf-8"))

    assert project_ato["dependencies"] == [
        {
            "type": "file",
            "path": "./packages/Raspberry_Pi_RP2040",
            "identifier": "local/raspberry-pi-rp2040",
        }
    ]


def test_create_local_package_backfills_existing_file_dependency_identifier(
    tmp_path: Path,
):
    project_root = tmp_path / "demo"
    project_root.mkdir()
    (project_root / "ato.yaml").write_text(
        """
requires-atopile: ^0.14.0
paths:
  src: ./
  layout: ./layouts
builds:
  default:
    entry: main.ato:App
dependencies:
  - type: file
    path: ./packages/Raspberry_Pi_RP2040
""".strip()
    )

    projects_domain.create_local_package(project_root, "Raspberry_Pi_RP2040", "RP2040")

    project_ato = yaml.safe_load((project_root / "ato.yaml").read_text(encoding="utf-8"))

    assert project_ato["dependencies"] == [
        {
            "type": "file",
            "path": "./packages/Raspberry_Pi_RP2040",
            "identifier": "local/raspberry-pi-rp2040",
        }
    ]
