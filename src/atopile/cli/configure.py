"""
Configure the user's system for atopile development.
"""

from pathlib import Path
from textwrap import dedent

import rich
import rich.prompt

import atopile.version
import click

CONFIGURED_FOR_PATH = Path("~/.atopile/configured_for").expanduser().absolute()


def get_configured_for_version() -> atopile.version.Version:
    """Return the version of atopile that the user's system is configured for."""
    try:
        with CONFIGURED_FOR_PATH.open("r", encoding="utf-8") as f:
            version_str = f.read().strip()
    except FileNotFoundError:
        version_str = "0.0.0"
    return atopile.version.clean_version(atopile.version.Version.parse(version_str))


@click.command("configure")
def configure() -> None:
    """
    Configure the user's system for atopile development.
    """
    do_configure()


def do_configure_if_needed() -> None:
    """Configure the user's system for atopile development if it's not already configured."""
    if not CONFIGURED_FOR_PATH.parent.exists():
        rich.print(dedent(
            """
            Welcome! :partying_face:

            Looks like you're new to atopile, there's some initial setup we need to do.

            The following changes will be made:
            - Install the atopile KiCAD plugin for you
            """
        ))
        if rich.prompt.Confirm.ask(
            ":wrench: That cool :sunglasses:?", default="y"
        ):
            do_configure()
            return
        else:
            rich.print(":thumbs_up: No worries, you can always run `ato configure` later!")
            CONFIGURED_FOR_PATH.parent.mkdir(exist_ok=True, parents=True)
            return

    if not CONFIGURED_FOR_PATH.exists():
        # In this case the user has opted for not installing things
        return

    # Otherwise we're configured, but we might need to update
    do_configure()


def do_configure() -> None:
    """Perform system configuration required for atopile."""
    if get_configured_for_version() == atopile.version.get_installed_atopile_version():
        return

    CONFIGURED_FOR_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CONFIGURED_FOR_PATH.open("w", encoding="utf-8") as f:
        f.write(
            str(
                atopile.version.clean_version(
                    atopile.version.get_installed_atopile_version()
                )
            )
        )

    # Otherwise, figure it out

    # FIXME: no idea what's up with this - but seem to help on Windows
    try:
        install_kicad_plugin()
    except FileNotFoundError:
        install_kicad_plugin()


PLUGIN_LOADER = f"""
plugin_path = "{Path(__file__).parent.parent}"
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
    kicad_plugin_dir = (
        Path("~/Documents/KiCad/7.0/scripting/plugins").expanduser().absolute()
    )

    # Create the directory if it doesn't exist
    kicad_plugin_dir.mkdir(parents=True, exist_ok=True)

    # Write the plugin loader
    with (kicad_plugin_dir / "atopile.py").open("w", encoding="utf-8") as f:
        f.write(PLUGIN_LOADER)
