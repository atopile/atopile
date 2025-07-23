"""
Configure the user's system for atopile development.
"""

import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from textwrap import dedent

import questionary
from ruamel.yaml import YAML, YAMLError

import atopile.config
import atopile.version
from atopile.telemetry import capture
from faebryk.libs.logging import rich_print_robust
from faebryk.libs.paths import get_config_dir

yaml = YAML()

CONFIGURED_FOR_PATH = get_config_dir() / "configured_for.yaml"


logger = logging.getLogger(__name__)


@dataclass
class Config:
    version: str | None = None
    install_kicad_plugin: bool | None = None


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
    if config.version is None:
        raise ValueError("No version configured")

    return atopile.version.clean_version(atopile.version.Version.parse(config.version))


@capture("cli:configure_start", "cli:configure_end")
def configure() -> None:
    """
    Configure the user's system for atopile development.
    """
    logger.setLevel(logging.INFO)
    _load_config()
    do_configure()


def do_configure_if_needed() -> None:
    """
    Configure the user's system for atopile development if it's not already configured.
    """
    if not atopile.config.config.interactive:
        return

    if not CONFIGURED_FOR_PATH.exists():
        rich_print_robust(
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
            "🔧 Install KiCAD plugin?", default=True
        ).ask()

    if config.install_kicad_plugin:
        # FIXME: no idea what's up with this - but seem to help on Windows
        install_kicad_plugin()

    # final steps
    config.version = str(
        atopile.version.clean_version(atopile.version.get_installed_atopile_version())
    )
    _save_config()


@capture("cli:install_kicad_plugin_start", "cli:install_kicad_plugin_end")
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

    kicad_config_search_path = [
        "~/Documents/KiCad/",
        "~/OneDrive/Documents/KiCad/",
        "~/.local/share/kicad/",
    ]

    existing_paths = [
        plugins_path
        for p in kicad_config_search_path
        if (rp := Path(p).expanduser().resolve()).exists()
        for plugins_path in rp.glob("*/scripting/plugins")
    ]

    if not existing_paths:
        existing_paths = list(
            Path("~")
            .expanduser()
            .resolve()
            .glob("**/kicad/*/scripting/plugins", case_sensitive=False)
        )

    no_plugin_found = True
    for sp in existing_paths:
        try:
            _write_plugin(sp)
        except FileNotFoundError:
            continue
        no_plugin_found = False

    if no_plugin_found:
        logger.warning("KiCAD config path not found. Couldn't install plugin!")
