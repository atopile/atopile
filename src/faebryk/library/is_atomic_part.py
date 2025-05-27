# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from pathlib import Path
from typing import override

import faebryk.library._F as F  # noqa: F401
from atopile.config import config as Gcfg
from faebryk.core.module import Module
from faebryk.libs.codegen.pycodegen import sanitize_name
from faebryk.libs.util import once


class is_atomic_part(Module.TraitT.decless()):
    def __init__(
        self,
        manufacturer: str,
        partnumber: str,
        footprint: str,
        symbol: str,
        model: str | None = None,
    ) -> None:
        super().__init__()
        self._manufacturer = manufacturer
        self._partnumber = partnumber
        self._footprint = footprint
        self._symbol = symbol
        self._model = model

    @property
    @once
    def path(self) -> Path:
        # TODO remove duplication with part_lifecycle
        identifier = (
            f"{sanitize_name(self._manufacturer)}_{sanitize_name(self._partnumber)}"
        )
        part_dir = Gcfg.project.paths.parts
        return part_dir / identifier

    @property
    def fp_path(self) -> tuple[Path, str]:
        """
        returns path to footprint and library name
        """
        return self.path / self._footprint, self.path.name

    @override
    def on_obj_set(self):
        super().on_obj_set()

        obj = self.get_obj(Module)

        fp_path, fp_lib = self.fp_path
        fp = F.KicadFootprint.from_path(fp_path, lib_name=fp_lib)
        obj.get_trait(F.can_attach_to_footprint).attach(fp)

        # TODO symbol
