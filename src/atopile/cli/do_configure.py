"""
Configure the user's system for atopile development.
"""
from pathlib import Path
import atopile.version

CONFIGURED_FOR_PATH = Path("~/.atopile/configured_for").expanduser().absolute()

def get_configured_for_version() -> atopile.version.Version:
    """Return the version of atopile that the user's system is configured for."""
    try:
        with CONFIGURED_FOR_PATH.open("r", encoding="utf-8") as f:
            version_str = f.read().strip()
    except FileNotFoundError:
        version_str = "0.0.0"
    return atopile.version.clean_version(atopile.version.Version.parse(version_str))


def do_configure() -> None:
    """Perform system configuration required for atopile."""
    if get_configured_for_version() == atopile.version.get_installed_atopile_version():
        return

    CONFIGURED_FOR_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CONFIGURED_FOR_PATH.open("w", encoding="utf-8") as f:
        f.write(str(atopile.version.clean_version(atopile.version.get_installed_atopile_version())))

    # Otherwise, figure it out
    install_kicad_plugin()


PLUGIN_LOADER = f"""
plugin_path = "{Path(__file__).parent.parent.parent}"
import sys
import importlib

if plugin_path not in sys.path:
    sys.path.append(plugin_path)

# if kicad_plugin is already in sys.modules, reload it
for module in sys.modules:
    if "kicad_plugin" in module:
        importlib.reload(sys.modules[module])

import kicad_plugin
"""


def install_kicad_plugin() -> None:
    """Install the kicad plugin."""
    # Find the path to kicad's plugin directory
    kicad_plugin_dir = Path("~/Documents/KiCad/7.0/scripting/plugins").expanduser().absolute()

    # Create the directory if it doesn't exist
    kicad_plugin_dir.mkdir(parents=True, exist_ok=True)

    # Write the plugin loader
    with (kicad_plugin_dir / "atopile.py").open("w", encoding="utf-8") as f:
        f.write(PLUGIN_LOADER)
