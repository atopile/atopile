# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Self

import faebryk.core.node as fabll
import faebryk.library._F as F

# from faebryk.core.reference import reference
from faebryk.libs.kicad.fileformats import kicad

# from faebryk.libs.units import to_si_str
from faebryk.libs.util import find, groupby, md_list, not_none

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer


class PCB(fabll.Node):
    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

    path_ = F.Parameters.StringParameter.MakeChild()
    pcb_file_ = F.Collections.Pointer.MakeChild()
    transformer_ = F.Collections.Pointer.MakeChild()
    app_ = F.Collections.Pointer.MakeChild()

    @classmethod
    def MakeChild(
        cls,
        path: Path,
        pcb_file: kicad.pcb.PcbFile,
        transformer: "PCB_Transformer",
        app: fabll.Node,
    ) -> fabll._ChildField[Self]:
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Expressions.Is.MakeChild_ConstrainToLiteral([out, cls.path_], path)
        )
        out.add_dependant(
            F.Collections.Pointer.EdgeField([out, cls.pcb_file_], [pcb_file])
        )
        out.add_dependant(
            F.Collections.Pointer.EdgeField([out, cls.transformer_], [transformer])
        )
        out.add_dependant(F.Collections.Pointer.EdgeField([out, cls.app_], [app]))
        return out

    def setup(self) -> Self:
        pcb = kicad.loads(kicad.pcb.PcbFile, Path(self.path))
        pcb_file = F.Parameters.Pointer.bind_typegraph_from_instance(
            instance=self.instance
        ).create_instance(g=self.instance.g())
        pcb_file.constrain_to_single(value=pcb)
        self.pcb_file_.get().point(pcb_file)

        transformer = PCB_Transformer(pcb.kicad_pcb, self.app)
        tf = F.Parameters.Pointer.bind_typegraph_from_instance(
            instance=self.instance
        ).create_instance(g=self.instance.g())
        tf.constrain_to_single(value=transformer)
        self.transformer_.get().point(tf)
        return self

    @property
    def transformer(self) -> "PCB_Transformer":
        # TODO
        return self.transformer_.get()

    @property
    def pcb_file(self) -> kicad.pcb.PcbFile:
        # TODO
        return self.pcb_file_.get()

    @property
    def path(self) -> Path:
        literal = self.path_.get().try_extract_constrained_literal()
        if literal is None:
            raise ValueError("PCB path is not set")
        return Path(literal.get_value())

    @property
    def app(self) -> fabll.Node:
        return fabll.Node.bind_instance(self.app_.get().deref().instance)

    class requires_drc_check(fabll.Node):
        _is_trait = fabll._ChildField(fabll.ImplementsTrait).put_on_type()
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

        @F.implements_design_check.register_post_pcb_check
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
        _is_trait = fabll._ChildField(fabll.ImplementsTrait).put_on_type()

        pcb_ptr_ = F.Collections.Pointer.MakeChild()

        class has_pcb_ref(fabll.Node):
            _is_trait = fabll._ChildField(fabll.ImplementsTrait).put_on_type()
            # reference: "PCB" = reference()

        @classmethod
        def MakeChild(cls, pcb: "PCB") -> fabll._ChildField[Self]:
            out = fabll._ChildField(cls)
            out.add_dependant(
                F.Collections.Pointer.EdgeField([out, cls.pcb_ptr_], [pcb])
            )
            return out

        @property
        def pcbs(self) -> set["PCB"]:
            return {PCB.bind_instance(self.pcb_ptr_.get().deref().instance)}

        def get_pcb_by_path(self, path: Path) -> "PCB":
            return find(self.pcbs, lambda pcb: pcb.path == path)

        def setup(self, pcb: "PCB") -> Self:
            self.pcb_ptr_.get().point(pcb)
            return self
