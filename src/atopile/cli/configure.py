"""
Configure the user's system for atopile development.
"""

import logging
from pathlib import Path
from textwrap import dedent

from ruamel.yaml import YAML

from atopile.telemetry import capture
from faebryk.libs.kicad.ipc import enable_plugin_api
from faebryk.libs.kicad.paths import get_plugin_paths
from faebryk.libs.logging import rich_print_robust
from faebryk.libs.paths import get_config_dir

yaml = YAML()

# Cleanup legacy config file
_LEGACY_CFG_PATH = get_config_dir() / "configured_for.yaml"
if _LEGACY_CFG_PATH.exists():
    _LEGACY_CFG_PATH.unlink()


logger = logging.getLogger(__name__)


@capture("cli:configure_start", "cli:configure_end")
def configure() -> None:
    """
    Configure the user's system for atopile development.
    """
    logger.setLevel(logging.INFO)

    # Just here for legacy support
    rich_print_robust(
        dedent(
            """
            This command is deprecated and will be removed in a future version.
            Configuration/Setup should be automatically handled.
            """
        )
    )


def setup() -> None:
    try:
        install_kicad_plugin()
    except Exception as e:
        logger.warning(f"Couldn't install plugin: {e}")

    try:
        enable_plugin_api()
    except Exception as e:
        logger.warning(f"Couldn't enable plugin api: {e}")


@capture("cli:install_kicad_plugin_start", "cli:install_kicad_plugin_end")
def install_kicad_plugin() -> None:
    """Install the kicad plugin."""
    # Find the path to kicad's plugin directory
    plugin_loader = dedent(f"""
        plugin_path = r"{Path(__file__).parent.parent}"
        import sys
        import importlib

        if plugin_path not in sys.path:
            sys.path.append(plugin_path)

        # if kicad_plugin is already in sys.modules, reload it
        for module in sys.modules:
            if "kicad_plugin" in module:
                importlib.reload(sys.modules[module])

        import kicad_plugin
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
        plugin_paths = get_plugin_paths()
    except FileNotFoundError:
        raise Exception("KiCAD config path not found. Couldn't install plugin!")

    for plugin_dir in plugin_paths:
        _write_plugin(plugin_dir)
