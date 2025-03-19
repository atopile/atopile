# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import os
import sys
from pathlib import Path

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
