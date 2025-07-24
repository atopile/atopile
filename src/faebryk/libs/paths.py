# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import os
import shutil
import sys
from pathlib import Path

import platformdirs

from faebryk.libs.util import once


@once
def get_config_dir() -> Path:
    out = None
    try:
        out = Path(platformdirs.user_config_dir("atopile"))
    except Exception:
        pass

    if not out or sys.platform == "darwin":
        out = (
            Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "atopile"
        )

    # handle legacy
    if sys.platform in ["linux", "darwin"]:
        legacy_path = Path.home() / "atopile"
        if legacy_path.exists():
            if out.exists():
                # remove old
                shutil.rmtree(legacy_path)
            else:
                # move old to new
                shutil.move(legacy_path, out)

    return out


def get_data_dir() -> Path:
    try:
        return Path(platformdirs.user_data_dir("atopile"))
    except Exception:
        return Path.home() / ".local" / "share" / "atopile"


def get_cache_dir() -> Path:
    try:
        return Path(platformdirs.user_cache_dir("atopile"))
    except Exception:
        return Path.home() / ".cache" / "atopile"
