# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from pathlib import Path

import faebryk

logger = logging.getLogger(__name__)

_RESOURCES_SUFFIX = "test/common/resources"


def ROOT_PATH() -> Path:
    editable_root = Path(faebryk.__file__).parent.parent.parent
    if (editable_root / _RESOURCES_SUFFIX).exists():
        return editable_root
    cwd_root = Path.cwd()
    if (cwd_root / _RESOURCES_SUFFIX).exists():
        return cwd_root
    raise FileNotFoundError("Could not find root directory")


RESOURCES_PATH = ROOT_PATH() / _RESOURCES_SUFFIX
FILEFORMATS_PATH = RESOURCES_PATH / "fileformats/kicad"


def _VERSION_DIR(version: int) -> Path:
    return FILEFORMATS_PATH / f"v{version}"


DEFAULT_VERSION = 9


def _FP_DIR(version: int = DEFAULT_VERSION) -> Path:
    return _VERSION_DIR(version) / "fp"


def _NETLIST_DIR(version: int = DEFAULT_VERSION) -> Path:
    return _VERSION_DIR(version) / "netlist"


def _SCH_DIR(version: int = DEFAULT_VERSION) -> Path:
    return _VERSION_DIR(version) / "sch"


def _SYM_DIR(version: int = DEFAULT_VERSION) -> Path:
    return _VERSION_DIR(version) / "sym"


def _PRJ_DIR(version: int = DEFAULT_VERSION) -> Path:
    return _VERSION_DIR(version) / "prj"


def _FPLIB_DIR(version: int = DEFAULT_VERSION) -> Path:
    return _VERSION_DIR(version) / "fplib"


def _PCB_DIR(version: int = DEFAULT_VERSION) -> Path:
    return _VERSION_DIR(version) / "pcb"


PRJFILE = _PRJ_DIR() / "test.kicad_pro"
PCBFILE = _PCB_DIR() / "test.kicad_pcb"
FPFILE = _FP_DIR() / "test.kicad_mod"
NETFILE = _NETLIST_DIR() / "test_e.net"
FPLIBFILE = _FPLIB_DIR(7) / "fp-lib-table"
SCHFILE = _SCH_DIR() / "test.kicad_sch"
SYMFILE = _SYM_DIR() / "test.kicad_sym"
