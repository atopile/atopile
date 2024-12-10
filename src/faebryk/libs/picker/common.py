# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from enum import StrEnum
from textwrap import indent
from typing import TYPE_CHECKING, Iterable

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.parameter import (
    And,
    ConstrainableExpression,
    Is,
    Parameter,
    Predicate,
)
from faebryk.core.solver.solver import LOG_PICK_SOLVE, Solver
from faebryk.libs.e_series import E_SERIES, e_series_intersect
from faebryk.libs.picker.lcsc import LCSC_NoDataException, LCSC_PinmapException, attach
from faebryk.libs.picker.picker import (
    PickError,
    has_part_picked,
    has_part_picked_defined,
)
from faebryk.libs.sets.quantity_sets import (
    Quantity_Interval_Disjoint,
    Quantity_Singleton,
)
from faebryk.libs.units import to_si_str
from faebryk.libs.util import ConfigFlagEnum, cast_assert

if TYPE_CHECKING:
    from faebryk.libs.picker.jlcpcb.jlcpcb import Component, MappingParameterDB

logger = logging.getLogger(__name__)


class PickerType(StrEnum):
    SQLITE = "sqlite"
    API = "api"


DB_PICKER_BACKEND = ConfigFlagEnum(
    PickerType, "PICKER", PickerType.API, "Picker backend to use"
)
type SIvalue = str


class StaticPartPicker(F.has_multi_picker.Picker, ABC):
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
        desc = []
        if self.mfr:
            desc.append(f"mfr={self.mfr}")
        if self.mfr_pn:
            desc.append(f"mfr_pn={self.mfr_pn}")
        if self.lcsc_pn:
            desc.append(f"lcsc_pn={self.lcsc_pn}")
        return ", ".join(desc) or "<no params>"

    @abstractmethod
    def _find_parts(self, module: Module) -> list["Component"]:
        pass

    def pick(self, module: Module):
        parts = self._find_parts(module)

        if len(parts) > 1:
            raise PickError(
                f"Multiple parts found for {self._friendly_description()}", module
            )

        if len(parts) < 1:
            raise PickError(
                f"Could not find part for {self._friendly_description()}", module
            )

        (part,) = parts
        try:
            part.attach(module, [])
        except ValueError as e:
            raise PickError(
                f"Could not attach part for {self._friendly_description()}", module
            ) from e


def _build_compatible_constraint(
    target: Module, source: Module
) -> ConstrainableExpression:
    assert type(target) is type(source)

    # Override module parameters with picked component parameters
    module_params: dict[str, tuple[Parameter, Parameter]] = (
        target.zip_children_by_name_with(source, sub_type=Parameter)
    )

    # sort by type to avoid merge conflicts
    predicates: list[Predicate] = []
    it = module_params.values()
    for p, value in it:
        predicates.append(Is(p, value))

    return And(*predicates)


def _get_compatible_modules(
    module: Module, cache: list[Module], solver: Solver
) -> Iterable[Module]:
    compatible_constraints = [_build_compatible_constraint(module, m) for m in cache]
    if not compatible_constraints:
        return
    solve_result = solver.assert_any_predicate(
        list(zip(compatible_constraints, cache)), lock=True
    )
    for _, m in solve_result.true_predicates:
        yield m


class CachePicker(F.has_multi_picker.Picker):
    def __init__(self):
        super().__init__()
        self.cache = defaultdict[type[Module], set[Module]](set)

    def pick(self, module: Module, solver: Solver):
        mcache = [m for m in self.cache[type(module)] if m.has_trait(has_part_picked)]
        for m in _get_compatible_modules(module, mcache, solver):
            logger.debug(f"Found compatible part in cache: {module} with {m}")
            module.add(
                F.has_descriptive_properties_defined(
                    m.get_trait(F.has_descriptive_properties).get_properties()
                )
            )
            part = m.get_trait(has_part_picked).get_part()
            attach(module, part.partno)
            module.add(has_part_picked_defined(part))
            return

        self.cache[type(module)].add(module)
        raise PickError(f"No compatible part found in cache for {module}", module)

    @staticmethod
    def add_to_modules(modules: Iterable[Module], prio: int = 0):
        picker = CachePicker()
        for m in modules:
            m.add(F.has_multi_picker(prio, picker))


class PickerUnboundedParameterError(Exception):
    pass


class PickerESeriesIntersectionError(Exception):
    pass


def generate_si_values(
    value: Quantity_Interval_Disjoint, e_series: E_SERIES | None = None
) -> list[SIvalue]:
    if value.is_unbounded():
        raise PickerUnboundedParameterError(value)

    intersection = e_series_intersect(value, e_series)
    if intersection.is_empty():
        raise PickerESeriesIntersectionError(f"No intersection with E-series: {value}")
    si_unit = value.units

    si_vals = [
        to_si_str(Quantity_Singleton.cast(r).get_value(), si_unit)
        .replace("µ", "u")
        .replace("inf", "∞")
        for r in intersection
    ]

    return si_vals


def try_attach(
    module: Module,
    parts: Iterable["Component"],
    mapping: list["MappingParameterDB"],
    qty: int,
):
    # TODO remove ignore_exceptions
    # was used to handle TBDs
    from faebryk.libs.picker.jlcpcb.jlcpcb import Component

    failures = []
    for c in parts:
        try:
            c.attach(module, mapping, qty)
            return
        except (ValueError, Component.ParseError) as e:
            failures.append((c, e))
        except LCSC_NoDataException as e:
            failures.append((c, e))
        except LCSC_PinmapException as e:
            failures.append((c, e))

    if failures:
        fail_str = indent(
            "\n" + f"{'\n'.join(f'{c}: {e}' for c, e in failures)}", " " * 4
        )

        raise PickError(
            f"Failed to attach any components to module {module}: {len(failures)}"
            f" {fail_str}",
            module,
        )

    raise PickError(
        "No components found that match the parameters and that can be attached",
        module,
    )


def check_compatible_parameters(
    module: Module, c: "Component", mapping: list["MappingParameterDB"], solver: Solver
) -> bool:
    """
    Check if the parameters of a component are compatible with the module
    """
    # Nothing to check
    if not mapping:
        return True

    range_mapping = c.get_literal_for_mappings(mapping)

    param_mapping = [
        (
            (p := cast_assert(Parameter, getattr(module, m.param_name))),
            c_range if c_range is not None else p.domain.unbounded(p),
        )
        for m, c_range in range_mapping.items()
    ]

    known_incompatible = False

    # check for any param that has few supersets whether the component's range
    # is compatible already instead of waiting for the solver
    for m_param, c_range in param_mapping:
        # TODO other loglevel
        # logger.warning(f"Checking obvious incompatibility for param {m_param}")
        known_superset = solver.inspect_get_known_supersets(m_param, force_update=False)
        if not known_superset.is_superset_of(c_range):
            if LOG_PICK_SOLVE:
                logger.warning(
                    f"Known superset {known_superset} is not a superset of {c_range}"
                    f" for part C{c.lcsc}"
                )
            known_incompatible = True
            break

    # check for every param whether the candidate component's range is
    # compatible by querying the solver
    if not known_incompatible:
        anded = And(
            *(
                m_param.operation_is_superset(c_range)
                for m_param, c_range in param_mapping
            )
        )

        if LOG_PICK_SOLVE:
            logger.info(f"Solving for module: {module}")
        result = solver.assert_any_predicate([(anded, None)], lock=False)
        if not result.true_predicates:
            known_incompatible = True

    # debug
    if known_incompatible:
        logger.debug(
            f"Component {c.lcsc} doesn't match: "
            f"{[p for p, v in range_mapping.items()]}"
        )
        return False

    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"Found part {c.lcsc:8} "
            f"Basic: {bool(c.basic)}, Preferred: {bool(c.preferred)}, "
            f"Price: ${c.get_price(1):2.4f}, "
            f"{c.description:15},"
        )

    return True
