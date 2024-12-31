import math
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum, auto
from typing import Generator, Iterable, Mapping

import faebryk.library._F as F
from faebryk.core.node import NodeNoParent
from faebryk.core.trait import TraitImpl
from faebryk.libs.library import L
from faebryk.libs.util import FuncDict, groupby


class has_net_name(L.Trait.decless()):
    """Provide a net name suggestion or expectation"""

    class Level(Enum):
        IMPLICIT = auto()
        SUGGESTED = auto()
        EXPECTED = auto()

    def __init__(self, name: str, level: Level = Level.SUGGESTED):
        self.names = [(name, level)]

    @classmethod
    def suggest_name(
        cls, mif: L.ModuleInterface
    ) -> list[tuple[str | None, float]]:
        suggestions = []

        if t := mif.get_trait(cls):
            for name, level in t.names:
                if level == cls.Level.EXPECTED:
                    suggestions.append((name, math.inf))
                elif level == cls.Level.SUGGESTED:
                    suggestions.append((name, 1))

                try:
                    name = mif.get_name()
                except NodeNoParent:
                    # Skip no names
                    return [(None, 0)]

                if _shit_name(name):
                    return [(None, 0)]

        return suggestions

    def handle_duplicate(self, old: TraitImpl, node: L.Node) -> bool:
        assert isinstance(old, has_net_name)  # Trait, not trait impl check
        old.names.extend(self.names)
        return False


@dataclass
class _NetName:
    base_name: str | None = None
    prefix: str | None = None
    suffix: int | None = None

    @property
    def name(self) -> str:
        """
        Get the name of the net.
        Net names should take the form of: <prefix>-<base_name>-<suffix>
        There must always be some base, and if it's not provided, it's just 'net'
        Prefixes and suffixes are joined with a "-" if they exist.
        """
        return "-".join(
            str(n) for n in [self.prefix, self.base_name or "net", self.suffix] if n
        )


def _conflicts(
    names: Mapping[F.Net, _NetName],
) -> Generator[Iterable[F.Net], None, None]:
    for items in groupby(names.items(), lambda it: it[1].name).values():
        if len(items) > 1:
            yield [net for net, _ in items]


def _shit_name(name: str | None) -> bool:
    """Caesar says 👎"""
    if name is None:
        return True

    # By the time we're here, we have a bunch of pads with the name net attached
    if name == "net":
        return True

    if name in {"p1", "p2"}:
        return True

    if name.startswith("unnamed"):
        return True

    return False


def _decay(depth: int) -> float:
    return 1 / (depth + 1)


def generate_net_names(nets: list[F.Net]) -> None:
    """
    Generate good net names, assuming that we're passed all the nets in a design
    """

    # Ignore nets with names already
    nets = [n for n in nets if not n.has_trait(F.has_overriden_name)]

    names = FuncDict[F.Net, _NetName]()

    # First generate candidate base names
    for net in nets:
        required_names: set[str] = set()

        implicit_name_candidates: Mapping[str, float] = defaultdict(float)
        case_insensitive_map: Mapping[str, str] = {}
        net_mifs = net.get_connected_interfaces()
        for mif in net_mifs:
            # Rate implicit names
            # lower case so we are not case sensitive
            try:
                name = mif.get_name()
            except NodeNoParent:
                # Skip no names
                continue

            lower_name = name.lower()
            case_insensitive_map[lower_name] = name

            if _shit_name(lower_name):
                # Skip ranking shitty names
                continue

            depth = len(mif.get_hierarchy())
            if mif.get_parent_of_type(L.ModuleInterface):
                # Give interfaces on the same level a fighting chance
                depth -= 1

            implicit_name_candidates[case_insensitive_map[lower_name]] += _decay(depth)

        names[net] = _NetName()
        if implicit_name_candidates:
            names[net].base_name = max(
                implicit_name_candidates, key=implicit_name_candidates.get
            )

    # Resolve as many conflict as possible by prefixing on the lowest common node's full name # noqa: E501  # pre-existing
    for conflict_nets in _conflicts(names):
        for net in conflict_nets:
            if lcn := L.Node.deepest_common_parent(net.get_connected_interfaces()):
                names[net].prefix = lcn[0].get_full_name()

    # Resolve remaining conflicts by suffixing on a number
    for conflict_nets in _conflicts(names):
        for i, net in enumerate(conflict_nets):
            names[net].suffix = i

    # Override the net names we've derived
    for net, name in names.items():
        # Limit name length to 255 chars
        if len(name.name) > 255:
            name_str = name.name[:200] + "..." + name.name[-50:]
        else:
            name_str = name.name
        net.add(F.has_overriden_name_defined(name_str))
