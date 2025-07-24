"""
Configure the user's system for atopile development.
"""

import logging
from pathlib import Path
from textwrap import dedent

from ruamel.yaml import YAML

from atopile.telemetry import capture
from faebryk.libs.app.pcb import find_pcbnew
from faebryk.libs.logging import rich_print_robust
from faebryk.libs.paths import get_config_dir
from faebryk.libs.util import try_or

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
    install_kicad_plugin()


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

    kicad_config_search_path = [
        "~/Documents/KiCad/",
        "~/OneDrive/Documents/KiCad/",
        "~/.local/share/kicad/",
    ]

    plugin_paths_existing = [
        plugins_path
        for p in kicad_config_search_path
        if (rp := Path(p).expanduser().resolve()).exists()
        for plugins_path in rp.glob("*/scripting/plugins")
    ]

    # if pcbnew installed, search deeper for plugin dir
    if not plugin_paths_existing and try_or(
        find_pcbnew, False, catch=FileNotFoundError
    ):
        plugin_paths_existing = list(
            Path("~")
            .expanduser()
            .resolve()
            .glob("**/kicad/*/scripting/plugins", case_sensitive=False)
        )

    no_plugin_found = True
    for plugin_dir in plugin_paths_existing:
        try:
            _write_plugin(plugin_dir)
        except FileNotFoundError:
            continue
        no_plugin_found = False

    if no_plugin_found:
        logger.warning("KiCAD config path not found. Couldn't install plugin!")
