# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from __future__ import annotations

from pathlib import Path
from typing import Self

import faebryk.core.node as fabll
import faebryk.library._F as F


class has_spice_model(fabll.Node):
    """Trait marking a module as having an external SPICE model file.

    Carries:
        model_path      — relative path to .LIB file from the part's source dir
        subcircuit_name — name of .SUBCKT to instantiate
        pin_map         — comma-separated "SUBCKT_PIN:ato_iface,..." mapping
        params          — comma-separated "KEY=VALUE,..." parameter overrides
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())
    is_immutable = fabll.Traits.MakeEdge(fabll.is_immutable.MakeChild()).put_on_type()

    model_path = F.Parameters.StringParameter.MakeChild()
    subcircuit_name = F.Parameters.StringParameter.MakeChild()
    pin_map = F.Parameters.StringParameter.MakeChild()
    params = F.Parameters.StringParameter.MakeChild()

    @classmethod
    def MakeChild(  # type: ignore[override]
        cls,
        model_path: str = "",
        subcircuit_name: str = "",
        pin_map: str = "",
        params: str = "",
    ) -> fabll._ChildField[Self]:
        out = fabll._ChildField(cls)
        if model_path:
            out.add_dependant(
                F.Literals.Strings.MakeChild_SetSuperset(
                    [out, cls.model_path], model_path
                )
            )
        if subcircuit_name:
            out.add_dependant(
                F.Literals.Strings.MakeChild_SetSuperset(
                    [out, cls.subcircuit_name], subcircuit_name
                )
            )
        if pin_map:
            out.add_dependant(
                F.Literals.Strings.MakeChild_SetSuperset(
                    [out, cls.pin_map], pin_map
                )
            )
        if params:
            out.add_dependant(
                F.Literals.Strings.MakeChild_SetSuperset(
                    [out, cls.params], params
                )
            )
        return out

    def setup(
        self,
        model_path: str,
        subcircuit_name: str,
        pin_map: str,
        params: str = "",
    ) -> Self:
        self.model_path.get().set_singleton(value=model_path)
        self.subcircuit_name.get().set_singleton(value=subcircuit_name)
        self.pin_map.get().set_singleton(value=pin_map)
        if params:
            self.params.get().set_singleton(value=params)
        return self

    def get_model_path(self) -> str:
        return self.model_path.get().extract_singleton()

    def get_subcircuit_name(self) -> str:
        return self.subcircuit_name.get().extract_singleton()

    def get_pin_map(self) -> dict[str, str]:
        """Parse pin_map string into dict: subckt_pin -> ato_interface_name."""
        raw = self.pin_map.get().extract_singleton()
        result: dict[str, str] = {}
        for pair in raw.split(","):
            pair = pair.strip()
            if ":" in pair:
                subckt_pin, ato_iface = pair.split(":", 1)
                result[subckt_pin.strip()] = ato_iface.strip()
        return result

    def get_params(self) -> dict[str, str]:
        """Parse params string into dict: key -> value."""
        raw = self.params.get().try_extract_singleton()
        if not raw:
            return {}
        result: dict[str, str] = {}
        for pair in raw.split(","):
            pair = pair.strip()
            if "=" in pair:
                key, val = pair.split("=", 1)
                result[key.strip()] = val.strip()
        return result

    def get_source_dir(self) -> Path:
        """Get source directory from owner's is_ato_block trait."""
        from atopile.compiler.ast_visitor import is_ato_block

        owner = fabll.Traits.bind(self).get_obj(fabll.Node)
        ato_block = owner.get_trait(is_ato_block)
        return Path(ato_block.get_source_dir())

    def get_model_file_path(self) -> Path:
        """Get full path to the model file (source_dir / model_path)."""
        return self.get_source_dir() / self.get_model_path()
