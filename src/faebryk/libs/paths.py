# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import sys
from pathlib import Path

import platformdirs

# TODO change to use platformdirs for linux
# and  ~/.config/atopile for darwin


def get_config_dir() -> Path:
    if sys.platform == "win32":
        return Path(platformdirs.user_config_dir("atopile"))
    elif sys.platform == "linux":
        return Path.home() / "atopile"
    elif sys.platform == "darwin":
        return Path.home() / "atopile"
    else:
        return Path.home() / "atopile"


def get_data_dir() -> Path:
    if sys.platform == "win32":
        return Path(platformdirs.user_data_dir("atopile"))
    elif sys.platform == "linux":
        return Path.home() / "atopile"
    elif sys.platform == "darwin":
        return Path.home() / "atopile"
    else:
        return Path.home() / "atopile"


def get_cache_dir() -> Path:
    if sys.platform == "win32":
        return Path(platformdirs.user_cache_dir("atopile"))
    elif sys.platform == "linux":
        return Path.home() / "atopile" / "cache"
    elif sys.platform == "darwin":
        return Path.home() / "atopile" / "cache"
    else:
        return Path.home() / "atopile" / "cache"
