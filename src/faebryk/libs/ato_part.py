# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import re
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from textwrap import indent
from typing import Self

from more_itertools import first

from faebryk.libs.kicad.fileformats_latest import (
    C_kicad_footprint_file,
    C_kicad_model_file,
)
from faebryk.libs.kicad.fileformats_sch import C_kicad_sym_file
from faebryk.libs.util import KeyErrorAmbiguous, KeyErrorNotFound, try_or

logger = logging.getLogger(__name__)


@dataclass
class AtoPart:
    identifier: str
    path: Path
    mfn: tuple[str, str]
    fp: C_kicad_footprint_file
    symbol: C_kicad_sym_file
    model: C_kicad_model_file | None

    @property
    def fp_path(self) -> Path:
        return self.path / f"{self.fp.footprint.base_name}.kicad_mod"

    @property
    def sym_path(self) -> Path:
        return (
            self.path
            / f"{first(self.symbol.kicad_symbol_lib.symbols.values()).name}.kicad_sym"
        )

    @property
    def ato_path(self) -> Path:
        return self.path / (self.path.name + ".ato")

    @property
    def model_path(self) -> Path:
        if not self.model:
            raise ValueError("Model is not set")
        return self.path / self.model.filename

    def __post_init__(self):
        self.fp = deepcopy(self.fp)
        self.fp.footprint.name = f"{self.identifier}:{self.fp.footprint.base_name}"
        if self.model:
            # TODO: do this the proper way
            from atopile.config import config as Gcfg

            prjroot = Gcfg.build.paths.fp_lib_table.parent
            self.fp.footprint.models[0].path = Path(
                "${KIPRJMOD}"
            ) / self.model_path.relative_to(prjroot, walk_up=True)

    def dump(self):
        self.path.mkdir(parents=True, exist_ok=True)

        self.fp.dumps(self.fp_path)
        self.symbol.dumps(self.sym_path)
        if self.model:
            self.model.dumps(self.model_path)

        # TODO use traits
        component = f"component {self.identifier}:\n"
        inner = [
            "pass",
        ]

        def _insert_key(key: str, value: str):
            inner.insert(-1, f"# {key}: {value}")

        _insert_key("fp", self.fp_path.name)
        _insert_key("symbol", self.sym_path.name)
        if self.model:
            _insert_key("model", self.model_path.name)
        _insert_key("manufacturer", self.mfn[0])
        _insert_key("partnumber", self.mfn[1])

        component += indent("\n".join(inner), prefix=" " * 4)

        self.ato_path.write_text(component)

    @classmethod
    def load(cls, path: Path) -> Self:
        def _find_by_ext(ext: str) -> Path:
            candidates = list(path.glob(f"*{ext}"))
            if not candidates:
                raise KeyErrorNotFound(f"No file with extension {ext} found in {path}")
            if len(candidates) > 1:
                raise KeyErrorAmbiguous(
                    candidates,
                    f"Multiple files with extension {ext} found in {path}",
                )
            return first(candidates)

        ato_path = _find_by_ext(".ato")
        ato = ato_path.read_text("utf-8")

        def _extract_key(key: str) -> str:
            # TODO handle multiple matches
            match = re.search(rf"    # {key}: (.*)", ato)
            if not match:
                raise KeyErrorNotFound(f"No {key} found in {ato_path}")
            return match.group(1)

        fp = C_kicad_footprint_file.loads(path / _extract_key("fp"))
        symbol = C_kicad_sym_file.loads(path / _extract_key("symbol"))
        model = try_or(
            lambda: C_kicad_model_file.loads(path / _extract_key("model")),
        )
        mfn_pn = _extract_key("manufacturer"), _extract_key("partnumber")

        return cls(
            identifier=path.name,
            path=path,
            mfn=mfn_pn,
            fp=fp,
            symbol=symbol,
            model=model,
        )
