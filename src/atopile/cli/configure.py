"""
Configure the user's system for atopile development.
"""

from atopile.logging import get_logger

logger = get_logger(__name__)


def setup() -> None:
    # Cleanup legacy config file
    from faebryk.libs.kicad.ipc import enable_plugin_api
    from faebryk.libs.paths import get_config_dir

    try:
        _LEGACY_CFG_PATH = get_config_dir() / "configured_for.yaml"
        if _LEGACY_CFG_PATH.exists():
            _LEGACY_CFG_PATH.unlink()
    except Exception as e:
        logger.warning(f"Couldn't remove legacy config file: {e!r}")

    # if running is ci skip plugin installation
    from atopile.telemetry import PropertyLoaders

    if PropertyLoaders.ci_provider():
        return
    try:
        install_kicad_plugin()
    except Exception as e:
        logger.warning(f"Couldn't install plugin: {e!r}")

    try:
        enable_plugin_api()
    except Exception as e:
        logger.warning(f"Couldn't enable plugin api: {e!r}")


def install_kicad_plugin() -> None:
    """Install the kicad plugin."""
    # TODO switch to new plugin as soon as group serialize ipc works in kicad
    # TODO then also remove legacy plugin from existing installations
    from atopile.kicad_plugin.lib import install_kicad_legacy_plugin

    install_kicad_legacy_plugin()
