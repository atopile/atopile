# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import ctypes
import logging
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, Self

import faebryk.core.node as fabll
import faebryk.library._F as F

# from faebryk.core.reference import reference
from faebryk.libs.kicad.fileformats import kicad

# from faebryk.libs.units import to_si_str
from faebryk.libs.util import find, groupby, md_list, not_none

if TYPE_CHECKING:
    from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer

logger = logging.getLogger(__name__)


class PCB(fabll.Node):
    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

    path_ = F.Parameters.StringParameter.MakeChild()
    pcb_file_ = F.Parameters.StringParameter.MakeChild()
    transformer_ = F.Parameters.StringParameter.MakeChild()
    app_ = F.Collections.Pointer.MakeChild()

    _transformer_registry: ClassVar[dict[int, "PCB_Transformer"]] = {}

    def setup(self, path: str, app: fabll.Node) -> Self:
        self.app_.get().point(app)
        self.path_.get().set_singleton(path)
        return self

    def run_transformer(self) -> Self:
        from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer

        pcbfile = kicad.loads(kicad.pcb.PcbFile, self.path)
        self.pcb_file_.get().set_singleton(value=str(id(pcbfile)))
        transformer = PCB_Transformer(pcbfile.kicad_pcb, self.app)
        self.transformer_.get().set_singleton(value=str(id(transformer)))
        self._transformer_registry[id(transformer)] = transformer
        return self

    @property
    def transformer(self) -> "PCB_Transformer":
        transformer_id = int(self.transformer_.get().extract_singleton())

        return ctypes.cast(transformer_id, ctypes.py_object).value

    @property
    def pcb_file(self) -> kicad.pcb.PcbFile:
        pcb_file_id = int(self.pcb_file_.get().extract_singleton())
        return ctypes.cast(pcb_file_id, ctypes.py_object).value

    @property
    def path(self) -> Path:
        literal = self.path_.get().try_extract_singleton()
        if literal is None:
            raise ValueError("PCB path is not set")
        return Path(literal)

    @property
    def app(self) -> fabll.Node:
        return fabll.Node.bind_instance(self.app_.get().deref().instance)

    class requires_drc_check(fabll.Node):
        is_trait = fabll._ChildField(fabll.ImplementsTrait).put_on_type()
        type Violation = kicad.drc.DrcFile.C_Violation

        class DrcException(F.implements_design_check.UnfulfilledCheckException):
            type Violation = PCB.requires_drc_check.Violation

            def __init__(
                self,
                pcb: "PCB",
                shorts: list[Violation],
                unconnected: list[Violation],
                units: str,
            ):
                self.shorts = shorts
                self.unconnected = unconnected
                self.units = units
                super().__init__(
                    (
                        f"{type(self).__name__} "
                        f"({len(self.shorts)} shorts, "
                        f"{len(self.unconnected)} unconnected)"
                    ),
                    nodes=[],
                )

            def pretty_violation(self, violation: Violation):
                def _convert_coord(c):
                    x, y = (to_si_str(subcoord, self.units) for subcoord in (c.x, c.y))
                    return f"({x},{y})"

                return {
                    violation.description: [
                        f"{i.description} @{_convert_coord(i.pos)}"
                        for i in violation.items
                    ]
                }

            def pretty(self) -> str:
                out = ""
                if self.shorts:
                    out += "\n\nShorts\n"
                    out += md_list(
                        [self.pretty_violation(v) for v in self.shorts],
                        recursive=True,
                    )
                if self.unconnected:
                    out += "\n\nMissing connections\n"
                    out += md_list(
                        [self.pretty_violation(v) for v in self.unconnected],
                        recursive=True,
                    )
                return out

            def __str__(self):
                return self.pretty()

        design_check: F.implements_design_check

        # FIXME: satisfy implements_design_check contract
        # @F.implements_design_check.register_post_pcb_check
        def __check_post_pcb__(self):
            from faebryk.libs.kicad.drc import run_drc as run_drc_kicad

            pcb = not_none(self.get_parent_of_type(PCB))
            assert pcb.path is not None, "PCB path is not set"

            drc_report = run_drc_kicad(pcb.path)

            grouped = groupby(drc_report.violations, lambda v: v.type)
            not_connected = drc_report.unconnected_items

            shorts = grouped.get(
                kicad.drc.DrcFile.C_Violation.C_Type.shorting_items, []
            )
            if shorts or not_connected:
                raise self.DrcException(
                    pcb, shorts, not_connected, drc_report.coordinate_units
                )

    # TODO use reference
    class has_pcb(fabll.Node):
        is_trait = fabll._ChildField(fabll.ImplementsTrait).put_on_type()

        pcb_ptr_ = F.Parameters.StringParameter.MakeChild()

        class has_pcb_ref(fabll.Node):
            is_trait = fabll._ChildField(fabll.ImplementsTrait).put_on_type()
            # reference: "PCB" = reference()

        @classmethod
        def MakeChild(cls, pcb: "PCB") -> fabll._ChildField[Self]:
            out = fabll._ChildField(cls)
            out.add_dependant(
                F.Literals.Strings.MakeChild_SetSuperset(
                    [out, cls.pcb_ptr_], str(id(pcb))
                )
            )
            return out

        @property
        def pcbs(self) -> set["PCB"]:
            pcb_id = int(self.pcb_ptr_.get().extract_singleton())
            return {ctypes.cast(pcb_id, ctypes.py_object).value}

        def get_pcb_by_path(self, path: Path) -> "PCB":
            return find(self.pcbs, lambda pcb: pcb.path == path)

        def setup(self, pcb: "PCB") -> Self:
            self.pcb_ptr_.get().set_singleton(value=str(id(pcb)))
            return self
