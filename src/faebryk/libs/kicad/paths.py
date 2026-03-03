# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import os
import sys
from pathlib import Path
from shutil import which
from tempfile import gettempdir

import platformdirs

from faebryk.libs.util import find, not_none, once

# @kicad10
KICAD_VERSION = "9.0"

# footprint library paths
# ref: https://docs.kicad.org/8.0/en/kicad/kicad.html#config-file-location
match sys.platform:
    case "win32":
        appdata = os.getenv("APPDATA")
        if appdata is not None:
            GLOBAL_FP_LIB_PATH = (
                Path(appdata) / "kicad" / KICAD_VERSION / "fp-lib-table"
            )
        else:
            raise EnvironmentError("APPDATA environment variable not set")
        # TODO: check on a windows machine
        GLOBAL_FP_DIR_PATH = Path(appdata) / "kicad" / KICAD_VERSION / "footprints"
    case "linux":
        GLOBAL_FP_LIB_PATH = (
            Path("~/.config/kicad").expanduser() / KICAD_VERSION / "fp-lib-table"
        )
        GLOBAL_FP_DIR_PATH = Path("/usr/share/kicad/footprints")
    case "darwin":
        GLOBAL_FP_LIB_PATH = (
            Path("~/Library/Preferences/kicad").expanduser()
            / KICAD_VERSION
            / "fp-lib-table"
        )
        GLOBAL_FP_DIR_PATH = Path(
            "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
        )
    case _:
        raise EnvironmentError(f"Unsupported platform: {sys.platform}")


@once
def find_pcbnew() -> Path:
    """Figure out what to call for the pcbnew CLI."""
    if sys.platform.startswith("linux"):
        path = which("pcbnew")
        if path is None:
            raise FileNotFoundError("Could not find pcbnew executable")
        return Path(path)

    if sys.platform.startswith("darwin"):
        base = Path("/Applications/KiCad/")
    elif sys.platform.startswith("win"):
        base = Path(not_none(os.getenv("ProgramFiles"))) / "KiCad"
    else:
        raise NotImplementedError(f"Unsupported platform: {sys.platform}")

    if path := list(base.glob("**/pcbnew")):
        # TODO: find the best version
        return path[0]

    raise FileNotFoundError("Could not find pcbnew executable")


def _get_user_search_paths() -> list[Path]:
    """Get user-configured extra KiCad search paths from config.yaml."""
    try:
        from atopile.config import config

        return list(config.project.kicad.search_paths)
    except Exception:
        return []


def _get_versioned_dirs(base_paths: list[str | Path]) -> list[Path]:
    """Resolve base paths to versioned KiCad directories."""
    extra = _get_user_search_paths()
    all_paths: list[str | Path] = [*extra, *base_paths]
    return [Path(p).expanduser().resolve() / KICAD_VERSION for p in all_paths]


_CONFIG_BASE_PATHS: list[str | Path] = [
    # linux
    platformdirs.user_config_dir("kicad", roaming=True),
    # windows
    Path(platformdirs.user_config_dir("kicad", roaming=True)).parent,
    # macos
    "~/Library/Preferences/kicad/",
]

_DATA_BASE_PATHS: list[str | Path] = [
    # windows / macos
    Path(platformdirs.user_documents_dir()) / "KiCad",
    "~/OneDrive/Documents/KiCad/",
    # linux
    platformdirs.user_data_dir("kicad"),
]


@once
def get_config_path():
    return find(
        _get_versioned_dirs(_CONFIG_BASE_PATHS),
        lambda p: p.exists(),
    )


def get_config(name: str):
    path = get_config_path()

    cfg = path / name
    if not cfg.exists():
        raise FileNotFoundError(f"Could not find config path for {name}")
    return cfg


def get_config_common():
    return get_config("kicad_common.json")


def get_plugin_paths(legacy: bool = False):
    plugin_suffix = "scripting/plugins" if legacy else "plugins"

    # Check if the versioned kicad dir exists (even if plugin subdir doesn't yet).
    # The caller (install) creates the plugin subdir via mkdir -p, so we just need
    # to find the right kicad data root.
    plugin_paths = [
        d / plugin_suffix for d in _get_versioned_dirs(_DATA_BASE_PATHS) if d.exists()
    ]

    if not plugin_paths:
        raise FileNotFoundError(
            "Could not find KiCad plugin path. "
            "If KiCad is installed at a custom location,"
            " you may need to add the search path to your config.yaml file."
        )

    return plugin_paths


def get_ipc_socket_path():
    # windows / linux
    if sys.platform.startswith("win"):
        return Path(gettempdir()) / "kicad"
    # macos / linux
    return Path("/tmp") / "kicad"
