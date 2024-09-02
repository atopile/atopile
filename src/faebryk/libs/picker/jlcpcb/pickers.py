import logging

import faebryk.library._F as F
import faebryk.libs.picker.jlcpcb.picker_lib as P
from faebryk.core.module import Module
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


class StaticJLCPCBPartPicker(F.has_multi_picker.Picker):
    """
    Use this if you want to specify a specific part to the multi-picker
    eg. a default switch
    """

    def __init__(
        self,
        *,
        mfr: str | None = None,
        mfr_pn: str | None = None,
        lcsc_pn: str | None = None,
    ) -> None:
        super().__init__()
        self.mfr = mfr
        self.mfr_pn = mfr_pn
        self.lcsc_pn = lcsc_pn

    def _friendly_description(self) -> str:
        desc = ""
        if self.mfr:
            desc += f"mfr={self.mfr}"
        if self.mfr_pn:
            desc += f"mfr_pn={self.mfr_pn}"
        if self.lcsc_pn:
            desc += f"lcsc_pn={self.lcsc_pn}"
        if not desc:
            return "<no params>"
        return desc

    def pick(self, module: Module):
        q = ComponentQuery()

        if self.mfr:
            q.filter_by_manufacturer(self.mfr)
        if self.mfr_pn:
            q.filter_by_manufacturer_pn(self.mfr_pn)
        if self.lcsc_pn:
            q.filter_by_lcsc_pn(self.lcsc_pn)

        parts = q.get()

        if len(parts) > 1:
            raise PickError(
                f"Multiple parts found for {self._friendly_description()}", module
            )

        if len(parts) < 1:
            raise PickError(
                f"Could not find part for {self._friendly_description()}", module
            )

        try:
            parts[0].attach(module, [])
            return
        except ValueError as e:
            raise PickError(
                f"Could not attach part for {self._friendly_description()}", module
            ) from e


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
