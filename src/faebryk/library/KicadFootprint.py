# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from os import PathLike
from pathlib import Path
from typing import TYPE_CHECKING

import faebryk.library._F as F
from faebryk.libs.library import L
from faebryk.libs.util import times

if TYPE_CHECKING:
    from faebryk.libs.kicad.fileformats import C_kicad_footprint_file


class KicadFootprint(F.Footprint):
    # TODO: use common base trait class for all these
    # The type-checker wasn't picking up on the base-classes init attributes properly

    class has_footprint_file(F.Footprint.TraitT.decless()):
        """Direct reference to a KiCAD footprint file"""

        def __init__(self, file: PathLike):
            super().__init__()
            self.file = Path(file)

    class has_wrl_model_file(F.Footprint.TraitT.decless()):
        """Direct reference to a KiCAD wrl model file"""

        def __init__(self, file: PathLike):
            super().__init__()
            self.file = Path(file)

    class has_step_model_file(F.Footprint.TraitT.decless()):
        """Direct reference to a KiCAD step model file"""

        def __init__(self, file: PathLike):
            super().__init__()
            self.file = Path(file)

    class has_kicad_identifier(F.Footprint.TraitT.decless()):
        def __init__(self, kicad_identifier: str):
            super().__init__()
            if ":" not in kicad_identifier:
                raise ValueError(
                    'kicad_identifier must be in the format "library:footprint".'
                    " If not, it'll cause downstream problems"
                )
            self.kicad_identifier = kicad_identifier

        def on_obj_set(self):
            # Implicit trait of has_kicad_footprint is added w/ this trait
            # If this changes, create_footprint_library will need to be updated
            fp = self.get_obj(KicadFootprint)
            if not fp.has_trait(F.has_kicad_footprint):
                fp.add(
                    F.has_kicad_manual_footprint(
                        self.kicad_identifier,
                        {fp.pins[i]: pin_name for i, pin_name in fp.pin_names_sorted},
                    )
                )

    def __init__(self, pin_names: list[str]) -> None:
        super().__init__()

        unique_pin_names = sorted(set(pin_names))
        self.pin_names_sorted = list(enumerate(unique_pin_names))

    @L.rt_field
    def pins(self):
        return times(len(self.pin_names_sorted), F.Pad)

    @L.rt_field
    def attach_via_pinmap(self):
        return F.Footprint.can_attach_via_pinmap_pinlist(
            {pin_name: self.pins[i] for i, pin_name in self.pin_names_sorted}
        )

    @classmethod
    def from_file(cls, fp_file: "C_kicad_footprint_file") -> "KicadFootprint":
        """
        Create based on a footprint file

        Will take the pin names from that file.
        """

        pad_names = [pad.name for pad in fp_file.footprint.pads]
        self = cls(pad_names)
        return self

    @classmethod
    def from_path(cls, fp_path: PathLike) -> "KicadFootprint":
        """
        Create based on a footprint file

        Will take the pin names from that file.
        """
        from faebryk.libs.kicad.fileformats_version import kicad_footprint_file

        self = cls.from_file(kicad_footprint_file(Path(fp_path)))
        self.add(cls.has_footprint_file(fp_path))
        return self
