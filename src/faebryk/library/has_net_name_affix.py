# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Self

import faebryk.core.node as fabll
import faebryk.library._F as F


class has_net_name_affix(fabll.Node):
    """Require a fixed prefix/suffix to be applied to a derived net name.

    This does not set or suggest the base name, it enforces that when a name is
    generated it is of the form: `${required_prefix}${base}${required_suffix}`.

    Typical usage is for differential pairs, e.g. enforce `_p` / `_n` suffixes.
    Attach to an `F.Electrical` interface (e.g. a `.line`).
    """

    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    required_prefix_ = F.Parameters.StringParameter.MakeChild()
    required_suffix_ = F.Parameters.StringParameter.MakeChild()

    @property
    def prefix(self) -> F.Literals.Strings | None:
        return self.required_prefix_.get().try_extract_constrained_literal()

    @property
    def suffix(self) -> F.Literals.Strings | None:
        return self.required_suffix_.get().try_extract_constrained_literal()

    def setup(self, prefix: str | None = None, suffix: str | None = None) -> Self:
        if prefix is not None:
            self.required_prefix_.get().alias_to_single(value=prefix)
        if suffix is not None:
            self.required_suffix_.get().alias_to_single(value=suffix)
        return self

    # TODO: Implement this
    # def handle_duplicate(self, old: TraitImpl, node: fabll.Node) -> bool:
    #     # If re-added, keep the more specific (non-None) values; error on conflicts
    #     assert isinstance(old, has_net_name_affix)
    #     # Merge if compatible
    #     if (
    #         self.required_prefix
    #         and old.required_prefix
    #         and self.required_prefix != old.required_prefix
    #     ):
    #         # Different required prefixes are incompatible; let caller decide
    #         return super().handle_duplicate(old, node)
    #     if (
    #         self.required_suffix
    #         and old.required_suffix
    #         and self.required_suffix != old.required_suffix
    #     ):
    #         return super().handle_duplicate(old, node)

    #     # Prefer new non-None values
    #     if self.required_prefix is not None:
    #         old.required_prefix = self.required_prefix
    #     if self.required_suffix is not None:
    #         old.required_suffix = self.required_suffix
    #     return False
