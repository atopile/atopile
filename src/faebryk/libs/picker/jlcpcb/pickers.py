import logging

import faebryk.library._F as F
import faebryk.libs.picker.jlcpcb.picker_lib as P
from faebryk.core.module import Module
from faebryk.core.solver import Solver
from faebryk.libs.picker.common import StaticPartPicker
from faebryk.libs.picker.jlcpcb.jlcpcb import JLCPCB_DB, ComponentQuery
from faebryk.libs.picker.picker import PickError

logger = logging.getLogger(__name__)


class JLCPCBPicker(F.has_multi_picker.FunctionPicker):
    def pick(self, module: Module):
        try:
            super().pick(module)
        except ComponentQuery.ParamError as e:
            raise PickError(e.args[0], module) from e
        except ComponentQuery.Error as e:
            raise PickError(e.args[0], module) from e


class StaticJLCPCBPartPicker(StaticPartPicker):
    """
    Use this if you want to specify a specific part to the multi-picker
    eg. a default switch
    """

    def _find_parts(self, module: Module):
        q = ComponentQuery()

        if self.mfr:
            q.filter_by_manufacturer(self.mfr)
        if self.mfr_pn:
            q.filter_by_manufacturer_pn(self.mfr_pn)
        if self.lcsc_pn:
            q.filter_by_lcsc_pn(self.lcsc_pn)

        return q.get()


def add_jlcpcb_pickers(module: Module, solver: Solver, base_prio: int = 0) -> None:
    # check if DB ok
    JLCPCB_DB()

    # Generic pickers
    prio = base_prio
    module.add(
        F.has_multi_picker(prio, JLCPCBPicker(P.find_and_attach_by_lcsc_id, solver))
    )
    module.add(F.has_multi_picker(prio, JLCPCBPicker(P.find_and_attach_by_mfr, solver)))

    # Type specific pickers
    prio = base_prio + 1

    F.has_multi_picker.add_pickers_by_type(
        module,
        P.TYPE_SPECIFIC_LOOKUP,
        lambda pick_fn: JLCPCBPicker(pick_fn, solver),
        prio,
    )
