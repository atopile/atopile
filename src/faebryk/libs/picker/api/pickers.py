# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
import faebryk.libs.picker.api.picker_lib as picker_lib
from faebryk.core.module import Module
from faebryk.libs.picker.api.api import ApiHTTPError
from faebryk.libs.picker.common import StaticPartPicker
from faebryk.libs.picker.jlcpcb.jlcpcb import Component
from faebryk.libs.picker.picker import PickError


class ApiPicker(F.has_multi_picker.FunctionPicker):
    def pick(self, module: Module):
        try:
            super().pick(module)
        except ApiHTTPError as e:
            if e.response.status_code == 404:
                raise PickError(str(e), module) from e
            else:
                raise


class StaticApiPartPicker(StaticPartPicker):
    """
    Picks a specific part by ID or manufacturer / part number
    """

    def _find_parts(self, module: Module) -> list[Component]:
        match self.mfr, self.mfr_pn, self.lcsc_pn:
            case (mfr, mfr_pn, None) if mfr is not None and mfr_pn is not None:
                return [picker_lib.find_component_by_mfr(mfr, mfr_pn)]
            case (None, None, lcsc_pn) if lcsc_pn is not None:
                return [picker_lib.find_component_by_lcsc_id(lcsc_pn)]
            case (None, None, None):
                raise PickError("No parameters provided", module)
        return []


def add_api_pickers(module: Module, base_prio: int = 0) -> None:
    # Generic pickers
    module.add(
        F.has_multi_picker(base_prio, ApiPicker(picker_lib.find_and_attach_by_lcsc_id))
    )
    module.add(
        F.has_multi_picker(base_prio, ApiPicker(picker_lib.find_and_attach_by_mfr))
    )

    # Type-specific pickers
    F.has_multi_picker.add_pickers_by_type(
        module, picker_lib.TYPE_SPECIFIC_LOOKUP, ApiPicker, base_prio + 1
    )
