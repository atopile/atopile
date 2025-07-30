"""
Configure the user's system for atopile development.
"""

import logging
from textwrap import dedent

from ruamel.yaml import YAML

from atopile.kicad_plugin.lib import install_kicad_legacy_plugin
from atopile.telemetry import capture
from faebryk.libs.kicad.ipc import enable_plugin_api
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
        logger.warning(f"Couldn't install plugin: {e!r}")

    try:
        enable_plugin_api()
    except Exception as e:
        logger.warning(f"Couldn't enable plugin api: {e!r}")


@capture("cli:install_kicad_plugin_start", "cli:install_kicad_plugin_end")
def install_kicad_plugin() -> None:
    """Install the kicad plugin."""
    # TODO switch to new plugin as soon as group serialize ipc works in kicad
    # TODO then also remove legacy plugin from existing installations
    install_kicad_legacy_plugin()
