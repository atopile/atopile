from enum import IntEnum, auto

from faebryk.core.trait import TraitImpl
from faebryk.libs.library import L


class has_net_name(L.Trait.decless()):
    """Provide a net name suggestion or expectation"""

    # TODO:
    # Currently this is just a data-class, which is EXPECRTED to be used by
    # src/faebryk/exporters/netlist/graph.py to compute the net names
    # The intelligence of graph.py should be split and moved here

    class Level(IntEnum):
        SUGGESTED = auto()
        EXPECTED = auto()

    def __init__(self, name: str, level: Level = Level.SUGGESTED):
        super().__init__()
        self.name = name
        self.level = level

    @classmethod
    def suggested(cls, name: str) -> "has_net_name":
        return cls(name, cls.Level.SUGGESTED)

    @classmethod
    def expected(cls, name: str) -> "has_net_name":
        return cls(name, cls.Level.EXPECTED)

    def handle_duplicate(self, old: TraitImpl, node: L.Node) -> bool:
        assert isinstance(old, has_net_name)  # Asserting trait, not impl
        # FIXME: gracefully handle hitting this multiple times
        return super().handle_duplicate(old, node)
