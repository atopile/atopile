from collections.abc import Generator
from queue import Empty, PriorityQueue
from types import SimpleNamespace
from typing import Callable, Iterable

import faebryk.library._F as F
from faebryk.core.node import Node
from faebryk.libs.library import L
from faebryk.libs.util import FuncDict, groupby

type NameGenerator = Generator[str, None, None]

type NameStrategyFunc = Callable[[F.Net, SimpleNamespace], NameGenerator]


class NameStrategy:
    def __init__(self, name: str, func: NameStrategyFunc):
        self.name = name
        self.generate = func
        self.cache = SimpleNamespace()

    def __call__(self, net: F.Net) -> NameGenerator:
        return self.generate(net, self.cache)


def strategy(name: str) -> Callable[[NameStrategyFunc], NameStrategy]:
    def decorator(func: NameStrategyFunc) -> NameStrategy:
        return NameStrategy(name, func)

    return decorator


@strategy("existing")
def existing(net: F.Net, cache: SimpleNamespace) -> NameGenerator:
    if (has_overriden_name := net.try_get_trait(F.has_overriden_name)) is not None:
        yield has_overriden_name.get_name()


@strategy("expected")
def expected(net: F.Net, cache: SimpleNamespace) -> NameGenerator:
    if getattr(cache, "expected_names", None) is None:
        cache.expected_names = PriorityQueue()

        expected_names = FuncDict[Node, str]()
        for mif in net.get_connected_interfaces():
            for node, has_net_name in mif.get_parents_with_trait(
                F.has_net_name, include_self=True
            ):
                if has_net_name.level == F.has_net_name.Level.EXPECTED:
                    expected_names[node] = has_net_name.name

        for node, name in expected_names.items():
            cache.expected_names.put((len(node.get_hierarchy()), name))

    while True:
        try:
            _, name = cache.expected_names.get(block=False)
            yield name
        except Empty:
            break


@strategy("suggested")
def suggested(net: F.Net, cache: SimpleNamespace) -> NameGenerator:
    if getattr(cache, "suggested_names", None) is None:
        cache.suggested_names = PriorityQueue()

        suggestions = FuncDict[Node, str]()
        for mif in net.get_connected_interfaces():
            for node, has_net_name in mif.get_parents_with_trait(
                F.has_net_name, include_self=True
            ):
                if has_net_name.level == F.has_net_name.Level.SUGGESTED:
                    suggestions[node] = has_net_name.name

        for node, name in suggestions.items():
            cache.suggested_names.put((len(node.get_hierarchy()), name))

    while True:
        try:
            _, name = cache.suggested_names.get(block=False)
            yield name
        except Empty:
            break


@strategy("best_mif")
def best_mif(net: F.Net, cache: SimpleNamespace) -> NameGenerator:
    if getattr(cache, "best_mif", None) is None:
        exclude = (F.Electrical, F.Pad, F.Footprint)
        mif_name_counter: dict[str, int] = {}

        for mif in net.get_connected_interfaces():
            for parent, _ in reversed(mif.get_hierarchy()[:-1]):
                if not isinstance(parent, exclude):
                    name = parent.get_name(accept_no_parent=True)
                    mif_name_counter.setdefault(name, 0)
                    mif_name_counter[name] += 1
                    break

        cache.mif_names = sorted(
            mif_name_counter, key=lambda k: mif_name_counter[k], reverse=True
        )

    while True:
        try:
            yield cache.mif_names.pop(0)
        except IndexError:
            break


@strategy("nearest_common_ancestor")
def nearest_common_ancestor(net: F.Net, cache: SimpleNamespace) -> NameGenerator:
    if (
        nca := L.Node.nearest_common_ancestor(*net.get_connected_interfaces())
    ) is not None:
        nca_node, nca_name = nca
        if nca_node.get_parent() is not None:
            yield nca_name


@strategy("concatenate_roots")
def concatenate_roots(net: F.Net, cache: SimpleNamespace) -> NameGenerator:
    roots = set()
    for mif in net.get_connected_interfaces():
        root = mif.get_hierarchy()[1][0]
        roots.add(root.get_name())

    if roots:
        yield "_".join(sorted(roots))


@strategy("fallback")
def fallback(net: F.Net, cache: SimpleNamespace) -> NameGenerator:
    # FIXME
    mif_names = [mif.get_full_name() for mif in net.get_connected_interfaces()]
    yield "_".join(mif_names)


class NameAssignment:
    STRATEGIES = [
        existing,
        expected,
        suggested,
        best_mif,
        nearest_common_ancestor,
        concatenate_roots,
        fallback,
    ]

    net: F.Net
    current_name: str
    tried_names: list[str]
    generator: NameGenerator

    _suffix = 0

    def __init__(self, net: F.Net):
        self.net = net
        self.tried_names = []
        self.generator = self._generate()

        next_name = next(self.generator)
        assert next_name is not None, "Unable to generate initial net name"

        self.current_name = next_name

    def _generate(self) -> NameGenerator:
        for strategy in self.STRATEGIES:
            yield from strategy(self.net)

    # def _generate_initial_name(self) -> str:
    #     """
    #     Returns the first generation of the first successful strategy for this net
    #     """
    #     for strategy in self.STRATEGIES:
    #         self._strategies =
    #         if (name := strategy(self.net)) is not None:
    #             self.origin = strategy.name
    #             self.tried_names.append(name)
    #             return name

    #     assert False, "Unable to generate initial net name"

    def deconflict(self):
        try:
            next_name = next(self.generator)
            self.current_name = next_name
        except StopIteration:
            raise
            self._suffix += 1
            return f"{self.current_name}_{self._suffix}"

    def attach(self) -> None:
        self.net.add(F.has_overriden_name_defined(self.current_name))

    def __rich_repr__(self):
        # yield self.origin
        yield self.current_name
        yield [mif.get_full_name() for mif in self.net.get_connected_interfaces()]


type NameAssignments = Iterable[NameAssignment]


def deconflicted(assignments: NameAssignments) -> NameAssignments:
    groups = groupby(assignments, lambda x: x.current_name)

    while any(len(group) > 1 for group in groups.values()):
        for group in groups:
            if len(group) > 1:
                for assignment in groups[group]:
                    before = assignment.current_name
                    assignment.deconflict()
                    after = assignment.current_name
                    print("deconflicting: ", before, "->", after)
        groups = groupby(assignments, lambda x: x.current_name)

    return assignments


def generate_assignments(nets: Iterable[F.Net]) -> NameAssignments:
    assignments = [NameAssignment(net) for net in nets]
    return deconflicted(assignments)
