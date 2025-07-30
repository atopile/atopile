import logging
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
from typing import Literal

from dataclasses_json import DataClassJsonMixin, LetterCase, dataclass_json

from faebryk.libs.kicad.paths import get_plugin_paths

logger = logging.getLogger(__name__)

RESOURCE_DIR = Path(__file__).parent / "resource"


@dataclass_json(letter_case=LetterCase.KEBAB)  # type: ignore
@dataclass
class KicadPluginManifest(DataClassJsonMixin):
    """
    https://gitlab.com/kicad/code/kicad/-/raw/master/api/schemas/api.v1.schema.json
    """

    @dataclass_json(letter_case=LetterCase.KEBAB)  # type: ignore
    @dataclass
    class Runtime(DataClassJsonMixin):
        type: Literal["python", "exec"]
        # min_version: str | None = None

    @dataclass_json(letter_case=LetterCase.KEBAB)  # type: ignore
    @dataclass
    class Action(DataClassJsonMixin):
        identifier: str
        name: str
        description: str
        show_button: bool
        scopes: list[
            Literal["pcb", "schematic", "footprint", "symbol", "project_manager"]
        ]
        entrypoint: str
        icons_light: list[str]
        icons_dark: list[str]

    identifier: str
    name: str
    description: str
    runtime: Runtime
    actions: list[Action]


@dataclass
class Command:
    command: list[str]
    kicad_action: KicadPluginManifest.Action
    icon_path: Path


def install_kicad_ipc_plugin() -> None:
    """Install the kicad plugin."""
    # Get the current Python interpreter path
    import sys

    python_path = sys.executable

    COMMANDS = [
        Command(
            command=["layout-sync"],
            kicad_action=KicadPluginManifest.Action(
                identifier="layout-sync",
                name="Layout Sync",
                description="Layout components on PCB in same spatial relationships as "
                "components on sub layouts. Warning: this will save the PCB file.",
                show_button=True,
                scopes=["pcb"],
                entrypoint="layout-sync.py",
                icons_light=[],
                icons_dark=[],
            ),
            icon_path=RESOURCE_DIR / "download.png",
        )
    ]

    manifest = KicadPluginManifest(
        identifier="atopile.kicad.plugin",
        name="atopile KiCad Plugin",
        description="KiCad plugin for atopile PCB design automation,"
        " providing layout synchronization and component placement tools.",
        runtime=KicadPluginManifest.Runtime(type="python"),
        actions=[cmd.kicad_action for cmd in COMMANDS],
    )

    for cmd in COMMANDS:
        icon_path = cmd.icon_path.expanduser().resolve().absolute()
        cmd.kicad_action.icons_light.append(str(icon_path))
        cmd.kicad_action.icons_dark.append(str(icon_path))

    base_cmd = [python_path, "-m", "atopile", "kicad-ipc"]

    manifest_str = manifest.to_json(indent=2)

    def _write_plugin(path: Path):
        # Create the directory if it doesn't exist
        path.mkdir(parents=True, exist_ok=True)

        (path / "requirements.txt").write_text("", encoding="utf-8")
        (path / "plugin.json").write_text(manifest_str, encoding="utf-8")

        for cmd in COMMANDS:
            exec_cmd = base_cmd + cmd.command
            command_loader = dedent(f"""
               #!/usr/bin/env python3
               import subprocess

               subprocess.run({exec_cmd!r})
               """)
            (path / cmd.kicad_action.entrypoint).write_text(
                command_loader, encoding="utf-8"
            )

    try:
        plugin_paths = get_plugin_paths()
    except FileNotFoundError:
        raise Exception("KiCAD config path not found. Couldn't install plugin!")

    for plugin_dir in plugin_paths:
        _write_plugin(plugin_dir / "atopile")


def install_kicad_legacy_plugin() -> None:
    """Install the kicad plugin."""
    # Get the current Python interpreter path
    import sys

    python_path = sys.executable

    # Find the path to kicad's plugin directory
    plugin_loader = dedent(f"""
        plugin_path = r"{Path(__file__).parent}"
        atopile_python = r"{python_path}"
        import sys
        import os
        import importlib

        # Store the Python interpreter path for subprocess calls
        os.environ["ATOPILE_PYTHON"] = atopile_python

        if plugin_path not in sys.path:
            sys.path.append(plugin_path)

        # if kicad_plugin is already in sys.modules, reload it
        for module in sys.modules:
            if "legacy" in module:
                importlib.reload(sys.modules[module])

        from legacy.plugin import activate
        activate()
        """)

    def _write_plugin(path: Path):
        # Create the directory if it doesn't exist
        path.mkdir(parents=True, exist_ok=True)

        # Write the plugin loader
        plugin_loader_path = path / "atopile.py"

        if not plugin_loader_path.exists():
            logger.info("Writing plugin loader to %s", plugin_loader_path)
        plugin_loader_path.write_text(plugin_loader, encoding="utf-8")

    try:
        plugin_paths = get_plugin_paths(legacy=True)
    except FileNotFoundError:
        raise Exception("KiCAD config path not found. Couldn't install plugin!")

    for plugin_dir in plugin_paths:
        _write_plugin(plugin_dir)
