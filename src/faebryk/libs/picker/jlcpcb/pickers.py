import logging

import faebryk.library._F as F
import faebryk.libs.picker.jlcpcb.picker_lib as P
from faebryk.core.core import Module
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


def add_jlcpcb_pickers(module: Module, base_prio: int = 0) -> None:
    # check if DB ok
    JLCPCB_DB()

    # Generic pickers
    prio = base_prio
    F.has_multi_picker.add_to_module(
        module,
        prio,
        JLCPCBPicker(P.find_lcsc_part),
    )
    F.has_multi_picker.add_to_module(
        module,
        prio,
        JLCPCBPicker(P.find_manufacturer_part),
    )

    # Type specific pickers
    prio = base_prio + 1

    F.has_multi_picker.add_pickers_by_type(
        module, P.TYPE_SPECIFIC_LOOKUP, JLCPCBPicker, prio
    )
