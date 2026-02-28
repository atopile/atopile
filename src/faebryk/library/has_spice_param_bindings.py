# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from __future__ import annotations

from typing import Self

import faebryk.core.node as fabll
import faebryk.library._F as F


class has_spice_param_bindings(fabll.Node):
    """Trait mapping SPICE subcircuit parameters to ato-level parameters.

    Place this on the module where the ato parameter is defined (e.g. the
    buck converter module that defines ``switching_frequency``), rather than
    on the low-level part component.

    Format: ``"FS:switching_frequency"`` or ``"FS:switching_frequency,GAIN:gain"``
    (same colon-separated format as ``has_spice_model.param_bindings``).
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())
    is_immutable = fabll.Traits.MakeEdge(fabll.is_immutable.MakeChild()).put_on_type()

    bindings = F.Parameters.StringParameter.MakeChild()

    @classmethod
    def MakeChild(  # type: ignore[override]
        cls,
        bindings: str = "",
    ) -> fabll._ChildField[Self]:
        out = fabll._ChildField(cls)
        if bindings:
            out.add_dependant(
                F.Literals.Strings.MakeChild_SetSuperset(
                    [out, cls.bindings], bindings
                )
            )
        return out

    def get_bindings(self) -> dict[str, str]:
        """Parse bindings string into dict: spice_param -> ato_param_name.

        Returns e.g. ``{"FS": "switching_frequency"}``.
        """
        raw = self.bindings.get().try_extract_singleton()
        if not raw:
            return {}
        result: dict[str, str] = {}
        for pair in raw.split(","):
            pair = pair.strip()
            if ":" in pair:
                spice_param, ato_param = pair.split(":", 1)
                result[spice_param.strip()] = ato_param.strip()
        return result
