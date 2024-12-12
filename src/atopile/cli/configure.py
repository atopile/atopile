"""
Configure the user's system for atopile development.
"""

import logging
from pathlib import Path
from textwrap import dedent
from typing import Optional

import questionary
import rich
from attrs import asdict, define
from ruamel.yaml import YAML, YAMLError

import atopile.version

yaml = YAML()

CONFIGURED_FOR_PATH = Path("~/.atopile/configured_for.yaml").expanduser().absolute()


logger = logging.getLogger(__name__)


@define
class Config:
    version: Optional[str] = None
    install_kicad_plugin: Optional[bool] = None


config = Config()


def _load_config() -> None:
    try:
        with CONFIGURED_FOR_PATH.open("r", encoding="utf-8") as f:
            _config = yaml.load(f)
    except (FileNotFoundError, YAMLError):
        _config = {}

    config.version = _config.get("version")
    config.install_kicad_plugin = _config.get("install_kicad_plugin")


def _save_config() -> None:
    CONFIGURED_FOR_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CONFIGURED_FOR_PATH.open("w", encoding="utf-8") as f:
        yaml.dump(asdict(config), f)


def get_configured_for_version() -> atopile.version.Version:
    """Return the version of atopile that the user's system is configured for."""
    return atopile.version.clean_version(atopile.version.Version.parse(config.version))


def configure() -> None:
    """
    Configure the user's system for atopile development.
    """
    logger.setLevel(logging.INFO)
    _load_config()
    do_configure()


def do_configure_if_needed() -> None:
    """Configure the user's system for atopile development if it's not already configured."""  # noqa: E501  # pre-existing
    if not CONFIGURED_FOR_PATH.exists():
        rich.print(
            dedent(
                """
            Welcome! :partying_face:

            Looks like you're new to atopile, there's some initial setup we need to do.
            """
            )
        )

    _load_config()

    try:
        if config.version == atopile.version.get_installed_atopile_version():
            return
    except TypeError:
        # Semver appears to do a __req__ by converting the lhs to a type, which
        # doesn't work for None
        pass

    # Otherwise we're configured, but we might need to update
    logger.setLevel(logging.WARNING)  # Quieten output for typical runs
    do_configure()


def do_configure() -> None:
    """Perform system configuration required for atopile."""
    if config.install_kicad_plugin is None:
        config.install_kicad_plugin = questionary.confirm(
            ":wrench: Install KiCAD plugin?", default=True
        ).ask()

    if config.install_kicad_plugin:
        # FIXME: no idea what's up with this - but seem to help on Windows
        install_kicad_plugin()

    # final steps
    config.version = str(
        atopile.version.clean_version(atopile.version.get_installed_atopile_version())
    )
    _save_config()


def install_kicad_plugin() -> None:
    """Install the kicad plugin."""
    # Find the path to kicad's plugin directory
    plugin_loader = f"""
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
        """

    def _write_plugin(path: Path):
        # Create the directory if it doesn't exist
        path.mkdir(parents=True, exist_ok=True)

        # Write the plugin loader
        plugin_loader_content = dedent(plugin_loader)
        plugin_loader_path = path / "atopile.py"

        logger.info("Writing plugin loader to %s", plugin_loader_path)
        with plugin_loader_path.open("w", encoding="utf-8") as f:
            f.write(plugin_loader_content)

    kicad_config_search_path = ["~/Documents/KiCad/", "~/.local/share/kicad/"]
    no_plugin_found = True
    for sp in kicad_config_search_path:
        config_path = Path(sp).expanduser().resolve()
        if config_path.exists():
            for p in config_path.glob("*/scripting/plugins"):
                try:
                    _write_plugin(p)
                except FileNotFoundError:
                    _write_plugin(p)
                no_plugin_found = False

    if no_plugin_found:
        logger.warning("KiCAD config path not found. Couldn't install plugin!")
