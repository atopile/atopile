# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import os
import sys
from pathlib import Path
from shutil import which
from tempfile import gettempdir

import platformdirs

from faebryk.libs.util import find, not_none, once, try_or

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


@once
def get_config_path():
    kicad_config_search_path = [
        # windows & linux
        platformdirs.user_config_dir("kicad", roaming=True),
        # macos
        "~/Library/Preferences/kicad/",
    ]

    mapped_paths = [
        (Path(p).expanduser().resolve() / KICAD_VERSION)
        for p in kicad_config_search_path
    ]

    return find(
        mapped_paths,
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


def get_plugin_paths():
    kicad_config_search_path = [
        # windows / macos
        Path(platformdirs.user_documents_dir()) / "KiCad",
        "~/OneDrive/Documents/KiCad/",
        # linux
        platformdirs.user_data_dir("kicad"),
    ]

    plugin_paths_existing = [
        rp
        for p in kicad_config_search_path
        if (
            rp := Path(p).expanduser().resolve()
            / KICAD_VERSION
            / "scripting"
            / "plugins"
        ).exists()
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

    if not plugin_paths_existing:
        raise FileNotFoundError("Could not find plugin paths")

    return plugin_paths_existing


def get_ipc_socket_path():
    # windows / linux
    if sys.platform.startswith("win"):
        return Path(gettempdir()) / "kicad"
    # macos / linux
    return Path("/tmp") / "kicad"
