# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.trait import TraitImpl
from faebryk.libs.library import L


class has_net_name_affix(L.Trait.decless()):
    """Require a fixed prefix/suffix to be applied to a derived net name.

    This does not set or suggest the base name, it enforces that when a name is
    generated it is of the form: `${required_prefix}${base}${required_suffix}`.

    Typical usage is for differential pairs, e.g. enforce `_p` / `_n` suffixes.
    Attach to an `F.Electrical` interface (e.g. a `.line`).
    """

    def __init__(
        self, required_prefix: str | None = None, required_suffix: str | None = None
    ):
        super().__init__()
        self.required_prefix = required_prefix
        self.required_suffix = required_suffix

    @classmethod
    def prefix(cls, value: str) -> "has_net_name_affix":
        return cls(required_prefix=value, required_suffix=None)

    @classmethod
    def suffix(cls, value: str) -> "has_net_name_affix":
        return cls(required_prefix=None, required_suffix=value)

    @classmethod
    def both(cls, prefix: str, suffix: str) -> "has_net_name_affix":
        return cls(required_prefix=prefix, required_suffix=suffix)

    def handle_duplicate(self, old: TraitImpl, node: L.Node) -> bool:
        # If re-added, keep the more specific (non-None) values; error on conflicts
        assert isinstance(old, has_net_name_affix)
        # Merge if compatible
        if (
            self.required_prefix
            and old.required_prefix
            and self.required_prefix != old.required_prefix
        ):
            # Different required prefixes are incompatible; let caller decide
            return super().handle_duplicate(old, node)
        if (
            self.required_suffix
            and old.required_suffix
            and self.required_suffix != old.required_suffix
        ):
            return super().handle_duplicate(old, node)

        # Prefer new non-None values
        if self.required_prefix is not None:
            old.required_prefix = self.required_prefix
        if self.required_suffix is not None:
            old.required_suffix = self.required_suffix
        return False
