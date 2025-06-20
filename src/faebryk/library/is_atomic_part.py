# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from pathlib import Path

import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module
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

    lazy: F.is_lazy

    @property
    @once
    def path(self) -> Path:
        from atopile.front_end import from_dsl

        if (from_dsl_ := self.try_get_trait(from_dsl)) is None:
            raise ValueError(
                "No source context found for module with is_atomic_part trait"
            )

        if from_dsl_.src_file is None:
            raise ValueError(
                "No source file found for module with is_atomic_part trait"
            )

        return from_dsl_.src_file.parent

    @property
    def fp_path(self) -> tuple[Path, str]:
        """
        returns path to footprint and library name
        """
        return self.path / self._footprint, self.path.name

    def on_obj_set(self):
        super().on_obj_set()

        obj = self.get_obj(Module)

        fp_path, fp_lib = self.fp_path
        fp = F.KicadFootprint.from_path(fp_path, lib_name=fp_lib)
        obj.get_trait(F.can_attach_to_footprint).attach(fp)

        # TODO symbol
