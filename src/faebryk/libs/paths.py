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
    def _cleanup_legacy_dir(legacy_path: Path, out: Path) -> None:
        known_files = [
            "config.yaml",
            "configured_for.yaml",
            "telemetry.yaml",
        ]

        for file in known_files:
            if (legacy_path / file).exists():
                if not (out / file).exists():
                    shutil.move(legacy_path / file, out / file)
                else:
                    (legacy_path / file).unlink()

        try:
            legacy_path.rmdir()
        except OSError:
            pass

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
        # chronological order
        for legacy_path in [Path.home() / ".atopile", Path.home() / "atopile"]:
            _cleanup_legacy_dir(legacy_path, out)

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
