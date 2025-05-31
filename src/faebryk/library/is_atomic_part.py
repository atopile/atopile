# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from pathlib import Path

import faebryk.library._F as F  # noqa: F401
from atopile.config import config as Gcfg
from faebryk.core.module import Module
from faebryk.libs.util import once, sanitize_filepath_part


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
        manufacturer = sanitize_filepath_part(self._manufacturer)
        partnumber = sanitize_filepath_part(self._partnumber)
        identifier = f"{manufacturer}_{partnumber}"

        part_dir = Gcfg.project.paths.parts
        return part_dir / identifier

    @property
    def fp_path(self) -> tuple[Path, str]:
        """
        returns path to footprint and library name
        """
        return self.path / self._footprint, self.path.name

    def attach(self):
        obj = self.get_obj(Module)

        fp_path, fp_lib = self.fp_path
        fp = F.KicadFootprint.from_path(fp_path, lib_name=fp_lib)
        obj.get_trait(F.can_attach_to_footprint).attach(fp)

        # TODO symbol
