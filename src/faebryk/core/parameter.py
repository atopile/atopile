# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging
from typing import (
    Callable,
    Optional,
    Sequence,
)

from typing_extensions import Self

from faebryk.core.graphinterface import GraphInterface
from faebryk.core.node import Node
from faebryk.core.trait import Trait
from faebryk.libs.util import TwistArgs, is_type_pair, try_avoid_endless_recursion

logger = logging.getLogger(__name__)


def _resolved[PV, O](
    func: Callable[["Parameter[PV]", "Parameter[PV]"], O],
) -> Callable[
    [
        "PV | set[PV] | tuple[PV, PV] | Parameter[PV]",
        "PV | set[PV] | tuple[PV, PV] | Parameter[PV]",
    ],
    O,
]:
    def wrap(*args):
        args = [Parameter.from_literal(arg).get_most_narrow() for arg in args]
        return func(*args)

    return wrap


class Parameter[PV](Node):
    type LIT = PV | set[PV] | tuple[PV, PV]
    type LIT_OR_PARAM = LIT | "Parameter[PV]"

    class TraitT(Trait): ...

    narrowed_by: GraphInterface
    narrows: GraphInterface

    class MergeException(Exception): ...

    class SupportsSetOps:
        def __contains__(self, other: "Parameter[PV].LIT_OR_PARAM") -> bool: ...

    def try_compress(self) -> "Parameter[PV]":
        return self

    @classmethod
    def from_literal(cls, value: LIT_OR_PARAM) -> '"Parameter[PV]"':
        from faebryk.library.Constant import Constant
        from faebryk.library.Range import Range
        from faebryk.library.Set import Set

        if isinstance(value, Parameter):
            return value
        elif isinstance(value, set):
            return Set(value)
        elif isinstance(value, tuple):
            return Range(*value)
        else:
            return Constant(value)

    def _merge(self, other: "Parameter[PV]") -> "Parameter[PV]":
        from faebryk.library.ANY import ANY
        from faebryk.library.Operation import Operation
        from faebryk.library.Set import Set
        from faebryk.library.TBD import TBD

        def _is_pair[T, U](type1: type[T], type2: type[U]) -> Optional[tuple[T, U]]:
            return is_type_pair(self, other, type1, type2)

        if self is other:
            return self

        try:
            if self == other:
                return self
        except ValueError:
            ...

        if pair := _is_pair(Parameter[PV], TBD):
            return pair[0]

        if pair := _is_pair(Parameter[PV], ANY):
            return pair[0]

        # TODO remove as soon as possible
        if pair := _is_pair(Parameter[PV], Operation):
            # TODO make MergeOperation that inherits from Operation
            # and return that instead, application can check if result is MergeOperation
            # if it was checking mergeability
            raise self.MergeException("cant merge range with operation")

        if pair := _is_pair(Parameter[PV], Parameter[PV].SupportsSetOps):
            out = self.intersect(*pair)
            if isinstance(out, Operation):
                raise self.MergeException("not resolvable")
            if out == Set([]) and not pair[0] == pair[1] == Set([]):
                raise self.MergeException(
                    f"conflicting sets/ranges: {self!r} {other!r}"
                )
            return out

        raise NotImplementedError

    def _narrowed(self, other: "Parameter[PV]"):
        if self is other:
            return

        if self.narrowed_by.is_connected(other.narrows):
            return
        self.narrowed_by.connect(other.narrows)

    @_resolved
    def is_mergeable_with(self: "Parameter[PV]", other: "Parameter[PV]") -> bool:
        try:
            self._merge(other)
            return True
        except self.MergeException:
            return False
        except NotImplementedError:
            return False

    @_resolved
    def is_subset_of(self: "Parameter[PV]", other: "Parameter[PV]") -> bool:
        from faebryk.library.ANY import ANY
        from faebryk.library.Operation import Operation
        from faebryk.library.TBD import TBD

        lhs = self
        rhs = other

        def is_either_instance(t: type["Parameter[PV]"]):
            return isinstance(lhs, t) or isinstance(rhs, t)

        # Not resolveable
        if isinstance(rhs, ANY):
            return True
        if isinstance(lhs, ANY):
            return False
        if is_either_instance(TBD):
            return False
        if is_either_instance(Operation):
            return False

        # Sets
        return lhs & rhs == lhs

    @_resolved
    def merge(self: "Parameter[PV]", other: "Parameter[PV]") -> "Parameter[PV]":
        out = self._merge(other)

        self._narrowed(out)
        other._narrowed(out)

        return out

    @_resolved
    def override(self: "Parameter[PV]", other: "Parameter[PV]") -> "Parameter[PV]":
        if not other.is_subset_of(self):
            raise self.MergeException("override not possible")

        self._narrowed(other)
        return other

    # TODO: replace with graph-based
    @staticmethod
    def arithmetic_op(
        op1: "Parameter[PV]", op2: "Parameter[PV]", op: Callable
    ) -> "Parameter[PV]":
        from faebryk.library.ANY import ANY
        from faebryk.library.Constant import Constant
        from faebryk.library.Operation import Operation
        from faebryk.library.Range import Range
        from faebryk.library.Set import Set
        from faebryk.library.TBD import TBD

        def _is_pair[T, U](
            type1: type[T], type2: type[U]
        ) -> Optional[tuple[T, U, Callable]]:
            if isinstance(op1, type1) and isinstance(op2, type2):
                return op1, op2, op
            if isinstance(op1, type2) and isinstance(op2, type1):
                return op2, op1, TwistArgs(op)

            return None

        if pair := _is_pair(Constant, Constant):
            return Constant(op(pair[0].value, pair[1].value))

        if pair := _is_pair(Range, Range):
            try:
                p0_min, p0_max = pair[0].min, pair[0].max
                p1_min, p1_max = pair[1].min, pair[1].max
            except Range.MinMaxError:
                return Operation(pair[:2], op)
            return Range(
                *(
                    op(lhs, rhs)
                    for lhs, rhs in [
                        (p0_min, p1_min),
                        (p0_max, p1_max),
                        (p0_min, p1_max),
                        (p0_max, p1_min),
                    ]
                )
            )

        if pair := _is_pair(Constant, Range):
            sop = pair[2]
            try:
                return Range(*(sop(pair[0], bound) for bound in pair[1].bounds))
            except Range.MinMaxError:
                return Operation(pair[:2], op)

        if pair := _is_pair(Parameter, ANY):
            sop = pair[2]
            return Operation(pair[:2], sop)

        if pair := _is_pair(Parameter, Operation):
            sop = pair[2]
            return Operation(pair[:2], sop)

        if pair := _is_pair(Parameter, TBD):
            sop = pair[2]
            return Operation(pair[:2], sop)

        if pair := _is_pair(Parameter, Set):
            sop = pair[2]
            return Set(
                Parameter.arithmetic_op(nested, pair[0], sop)
                for nested in pair[1].params
            )

        raise NotImplementedError

    @staticmethod
    def intersect(op1: "Parameter[PV]", op2: "Parameter[PV]") -> "Parameter[PV]":
        from faebryk.library.Constant import Constant
        from faebryk.library.Operation import Operation
        from faebryk.library.Range import Range
        from faebryk.library.Set import Set

        if op1 == op2:
            return op1

        def _is_pair[T, U](
            type1: type[T], type2: type[U]
        ) -> Optional[tuple[T, U, Callable]]:
            if isinstance(op1, type1) and isinstance(op2, type2):
                return op1, op2, op
            if isinstance(op1, type2) and isinstance(op2, type1):
                return op2, op1, TwistArgs(op)

            return None

        def op(a, b):
            return a & b

        # same types
        if pair := _is_pair(Constant, Constant):
            return Set([])
        if pair := _is_pair(Set, Set):
            return Set(pair[0].params.intersection(pair[1].params))
        if pair := _is_pair(Range, Range):
            try:
                min_ = max(pair[0].min, pair[1].min)
                max_ = min(pair[0].max, pair[1].max)
                if min_ > max_:
                    return Set([])
                if min_ == max_:
                    return Constant(min_)
                return Range(max_, min_)
            except Range.MinMaxError:
                return Operation(pair[:2], op)

        # diff types
        if pair := _is_pair(Constant, Range):
            try:
                if pair[0] in pair[1]:
                    return pair[0]
                else:
                    return Set([])
            except Range.MinMaxError:
                return Operation(pair[:2], op)
        if pair := _is_pair(Constant, Set):
            if pair[0] in pair[1]:
                return pair[0]
            else:
                return Set([])
        if pair := _is_pair(Range, Set):
            try:
                return Set(i for i in pair[1].params if i in pair[0])
            except Range.MinMaxError:
                return Operation(pair[:2], op)

        return Operation((op1, op2), op)

    @_resolved
    def __add__(self: "Parameter[PV]", other: "Parameter[PV]"):
        return self.arithmetic_op(self, other, lambda a, b: a + b)

    @_resolved
    def __radd__(self: "Parameter[PV]", other: "Parameter[PV]"):
        return self.arithmetic_op(self, other, lambda a, b: b + a)

    @_resolved
    def __sub__(self: "Parameter[PV]", other: "Parameter[PV]"):
        return self.arithmetic_op(self, other, lambda a, b: a - b)

    @_resolved
    def __rsub__(self: "Parameter[PV]", other: "Parameter[PV]"):
        return self.arithmetic_op(self, other, lambda a, b: b - a)

    # TODO PV | float
    @_resolved
    def __mul__(self: "Parameter[PV]", other: "Parameter[PV]"):
        return self.arithmetic_op(self, other, lambda a, b: a * b)

    @_resolved
    def __rmul__(self: "Parameter[PV]", other: "Parameter[PV]"):
        return self.arithmetic_op(self, other, lambda a, b: b * a)

    # TODO PV | float
    @_resolved
    def __truediv__(self: "Parameter[PV]", other: "Parameter[PV]"):
        return self.arithmetic_op(self, other, lambda a, b: a / b)

    @_resolved
    def __rtruediv__(self: "Parameter[PV]", other: "Parameter[PV]"):
        return self.arithmetic_op(self, other, lambda a, b: b / a)

    @_resolved
    def __pow__(self: "Parameter[PV]", other: "Parameter[PV]") -> "Parameter[PV]":
        return self.arithmetic_op(self, other, lambda a, b: a**b)

    @_resolved
    def __rpow__(self: "Parameter[PV]", other: "Parameter[PV]") -> "Parameter[PV]":
        return self.arithmetic_op(self, other, lambda a, b: b**a)

    @_resolved
    def __and__(self: "Parameter[PV]", other: "Parameter[PV]") -> "Parameter[PV]":
        return self.intersect(self, other)

    @_resolved
    def __rand__(self: "Parameter[PV]", other: "Parameter[PV]") -> "Parameter[PV]":
        return self.intersect(other, self)

    def get_most_narrow(self) -> "Parameter[PV]":
        out = self.get_narrowing_chain()[-1]

        com = out.try_compress()
        if com is not out:
            com = com.get_most_narrow()
            out._narrowed(com)
            out = com

        return out

    @staticmethod
    def resolve_all(params: "Sequence[Parameter[PV]]") -> "Parameter[PV]":
        from faebryk.library.TBD import TBD

        params_set = list(params)
        if not params_set:
            return TBD[PV]()
        it = iter(params_set)
        most_specific = next(it)
        for param in it:
            most_specific = most_specific.merge(param)

        return most_specific

    @try_avoid_endless_recursion
    def __str__(self) -> str:
        narrowest = self.get_most_narrow()
        if narrowest is self:
            return super().__str__()
        return str(narrowest)

    # @try_avoid_endless_recursion
    # def __repr__(self) -> str:
    #    narrowest = self.get_most_narrow()
    #    if narrowest is self:
    #        return super().__repr__()
    #    # return f"{super().__repr__()} -> {repr(narrowest)}"
    #    return repr(narrowest)

    def get_narrowing_chain(self) -> list["Parameter"]:
        from faebryk.core.util import get_direct_connected_nodes

        out: list[Parameter] = [self]
        narrowers = get_direct_connected_nodes(self.narrowed_by, Parameter)
        if narrowers:
            assert len(narrowers) == 1, "Narrowing tree diverged"
            out += next(iter(narrowers)).get_narrowing_chain()
            assert id(self) not in map(id, out[1:]), "Narrowing tree cycle"
        return out

    def get_narrowed_siblings(self) -> set["Parameter"]:
        from faebryk.core.util import get_direct_connected_nodes

        return get_direct_connected_nodes(self.narrows, Parameter)

    def __copy__(self) -> Self:
        return type(self)()

    def __deepcopy__(self, memo) -> Self:
        return self.__copy__()
