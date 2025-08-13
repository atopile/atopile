# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import re
from dataclasses import fields
from enum import StrEnum
from socket import gaierror

import more_itertools
from requests.exceptions import ConnectionError, ReadTimeout

import faebryk.library._F as F
from atopile.errors import UserInfraError
from faebryk.core.module import Module
from faebryk.core.parameter import And, Is, Parameter, ParameterOperatable
from faebryk.core.solver.solver import LOG_PICK_SOLVE, Solver
from faebryk.libs.exceptions import UserException, downgrade
from faebryk.libs.library import L
from faebryk.libs.picker.api.api import ApiHTTPError, get_api_client
from faebryk.libs.picker.api.models import (
    BaseParams,
    Component,
    LCSCParams,
    ManufacturerPartParams,
    make_params_for_type,
)
from faebryk.libs.picker.lcsc import (
    LCSC_NoDataException,
    LCSC_PinmapException,
    attach,
    check_attachable,
    get_raw,
)
from faebryk.libs.picker.picker import (
    NotCompatibleException,
    PickError,
    does_not_require_picker_check,
)
from faebryk.libs.sets.sets import EnumSet, P_Set
from faebryk.libs.smd import SMDSize
from faebryk.libs.test.times import Times
from faebryk.libs.util import (
    Tree,
    cast_assert,
    groupby,
    not_none,
)

logger = logging.getLogger(__name__)
client = get_api_client()


type SIvalue = str

# TODO add way for user to specify quantity of PCBAs
qty: int = 1


class PickerUnboundedParameterError(Exception):
    pass


class PickerESeriesIntersectionError(Exception):
    pass


def _extract_numeric_id(lcsc_id: str) -> int:
    match = re.match(r"C(\d+)", lcsc_id)
    if match is None:
        raise ValueError(f"Invalid LCSC part number {lcsc_id}")
    return int(match[1])


BackendPackage = StrEnum(
    "BackendPackage",
    {
        f"{prefix}{size.imperial.without_prefix}": (
            f"{prefix}{size.imperial.without_prefix}"
        )
        for prefix in ["R", "C", "L"]
        for size in SMDSize
        if size.name.startswith(("I", "M"))
    }
    | {
        size.value: size.value
        for size in SMDSize
        if not size.name.startswith(("I", "M"))
    },
)


def _from_smd_size(cls, size: SMDSize, type: type[L.Module]) -> "BackendPackage":
    if issubclass(type, F.Resistor):
        prefix = "R"
    elif issubclass(type, F.Capacitor):
        prefix = "C"
    elif issubclass(type, F.Inductor):
        prefix = "L"
    else:
        raise NotImplementedError(f"Unsupported pickable trait: {type}")

    try:
        return cls[f"{prefix}{size.imperial.without_prefix}"]
    except SMDSize.UnableToConvert:
        return cls[size.value]


BackendPackage.from_smd_size = classmethod(_from_smd_size)  # type: ignore


def _prepare_query(
    module: Module, solver: Solver
) -> BaseParams | LCSCParams | ManufacturerPartParams:
    assert module.has_trait(F.is_pickable)
    # Error can propagate through,
    # because we expect all pickable modules to be attachable
    check_attachable(module)

    if trait := module.try_get_trait(F.is_pickable_by_part_number):
        return ManufacturerPartParams(
            manufacturer_name=trait.get_manufacturer(),
            part_number=trait.get_partno(),
            quantity=qty,
        )

    elif trait := module.try_get_trait(F.is_pickable_by_supplier_id):
        if trait.get_supplier() == F.is_pickable_by_supplier_id.Supplier.LCSC:
            return LCSCParams(
                lcsc=_extract_numeric_id(trait.get_supplier_part_id()), quantity=qty
            )

    elif trait := module.try_get_trait(F.is_pickable_by_type):
        params_t = make_params_for_type(trait.pick_type)

        if pkg_t := module.try_get_trait(F.has_package_requirements):
            package = pkg_t.get_sizes(solver)
            package = EnumSet[BackendPackage](
                *[
                    BackendPackage.from_smd_size(SMDSize[s.name], trait.pick_type)
                    for s in package
                ]
            )
        else:
            package = None

        generic_field_names = {f.name for f in fields(params_t)}
        _, known_params = more_itertools.partition(
            lambda p: p.get_name() in generic_field_names, module.get_parameters()
        )
        cmp_params = {
            p.get_name(): p.get_last_known_deduced_superset(solver)
            for p in known_params
        }

        if all(superset is None for superset in cmp_params.values()):
            logger.warning(f"Module `{module}` has no constrained parameters")

        return params_t(package=package, qty=qty, **cmp_params)  # type: ignore

    raise NotImplementedError(
        f"Unsupported pickable trait: {module.get_trait(F.is_pickable)}"
    )


def _process_candidates(module: Module, candidates: list[Component]) -> list[Component]:
    # Filter parts with weird pinmaps
    it = iter(candidates)
    filtered_candidates = []
    for c in it:
        try:
            attach(module, c.lcsc_display, check_only=True, get_model=False)
            filtered_candidates.append(c)
            # If we found one that's ok, just continue since likely enough
            filtered_candidates.extend(it)
            break
        except LCSC_NoDataException as ex:
            if len(candidates) == 1:
                raise PickError(
                    (
                        "LCSC has no footprint/symbol for any candidate for "
                        f"`{module}`. Loosen your selection criteria or try another "
                        "part which has an LCSC footprint and symbol."
                    ),
                    module,
                ) from ex
        except LCSC_PinmapException:
            # if all filtered by pinmap something is fishy
            if not filtered_candidates and candidates[-1] is c:
                raise

    return filtered_candidates


def _find_modules(
    modules: Tree[Module], solver: Solver
) -> dict[Module, list[Component]]:
    timings = Times(name="find_modules")

    params = {m: _prepare_query(m, solver) for m in modules}
    timings.add("prepare queries")

    grouped = groupby(params.items(), lambda p: p[1])
    queries = list(grouped.keys())

    def _map_response[T](results: list[T]) -> dict[Module, T]:
        assert len(results) == len(queries)
        return {m: r for ms, r in zip(grouped.values(), results) for m, _ in ms}

    try:
        results = client.fetch_parts_multiple(queries)
        timings.add("fetch parts")
    except ConnectionError as e:
        cause = e.args[0]
        while not isinstance(cause, gaierror):
            cause = cause.__cause__
            if cause is None:
                break
        else:
            raise UserInfraError(
                f"Fetching component data failed: connection error: {cause.strerror}"
            ) from e

        raise UserInfraError("Fetching component data failed: connection error") from e
    except ReadTimeout as e:
        raise UserInfraError(
            "Fetching component data failed to complete in time. "
            "Please try again later."
        ) from e
    except ApiHTTPError as e:
        if e.response.status_code == 400:
            response = cast_assert(dict, e.response.json())
            if errors := response.get("detail", {}).get("errors", None):
                raise ExceptionGroup(
                    "Failed to fetch one or more parts",
                    [
                        PickError(
                            f"{error['message']} for {module.get_full_name()}"
                            f"\n{query.pretty_str()}",
                            module,
                        )
                        for module, (query, error) in _map_response(
                            list(zip(queries, errors))
                        ).items()
                        if error is not None
                    ],
                ) from e
            else:
                raise
        raise e

    out = {m: _process_candidates(m, r) for m, r in _map_response(results).items()}
    timings.add("process candidates")
    return out


def _attach(module: Module, c: Component):
    """
    Calls LCSC attach and wraps errors into PickError
    """

    try:
        c.attach(module)
    except (
        ValueError,
        Component.ParseError,
        LCSC_NoDataException,
        LCSC_PinmapException,
    ) as e:
        if LOG_PICK_SOLVE:
            logger.warning(f"Failed to attach {c} to `{module}`: {e}")

        raise PickError(
            f"Failed to attach component {c} to module `{module}`: {e}",
            module,
        )


def _get_compatible_parameters(
    module: Module, c: "Component", solver: Solver
) -> dict[Parameter, ParameterOperatable.Literal]:
    """
    Check if the parameters of a component are compatible with the module
    """
    # Nothing to check
    if not module.has_trait(F.is_pickable_by_type):
        return {}

    # shortcut because solving slow
    try:
        get_raw(c.lcsc_display)
    except LCSC_NoDataException as e:
        raise NotCompatibleException(module, c) from e

    design_params = {
        p.get_name() for p in module.get_trait(F.is_pickable_by_type).params
    }
    component_params = c.attribute_literals

    if no_attr := component_params.keys() - design_params:
        with downgrade(UserException):
            no_attr_str = "\n".join(f"- `{a}`" for a in no_attr)
            raise UserException(
                f"Module `{module}` is missing attributes:\n\n"
                f" {no_attr_str}\n\n"
                "This likely means you could use a more precise"
                " module/component in your design."
            )

    def _map_param(name: str, param: Parameter) -> tuple[Parameter, P_Set]:
        c_range = component_params.get(name)
        if c_range is None:
            c_range = param.domain.unbounded(param)
        return param, c_range

    param_mapping = [
        _map_param(name, param)
        for name, param in design_params.items()
        if not param.has_trait(does_not_require_picker_check)
    ]

    # check for any param that has few supersets whether the component's range
    # is compatible already instead of waiting for the solver
    for m_param, c_range in param_mapping:
        # TODO other loglevel
        # logger.warning(f"Checking obvious incompatibility for param {m_param}")
        known_superset = solver.inspect_get_known_supersets(m_param)
        if not known_superset.is_superset_of(c_range):
            if LOG_PICK_SOLVE:
                logger.warning(
                    f"Known superset {known_superset} is not a superset of {c_range}"
                    f" for part C{c.lcsc}"
                )
            raise NotCompatibleException(module, c, m_param, c_range)

    return {p: c_range for p, c_range in param_mapping}


def _check_candidates_compatible(
    module_candidates: list[tuple[Module, Component]],
    solver: Solver,
    allow_not_deducible: bool = False,
):
    """
    Check if combination of all candidates is compatible with each other
    Checks each candidate first for individual compatibility
    """

    if not module_candidates:
        return

    mappings = [_get_compatible_parameters(m, c, solver) for m, c in module_candidates]

    if LOG_PICK_SOLVE:
        logger.info(f"Solving for modules: {[m for m, _ in module_candidates]}")

    predicates = (
        Is(m_param, c_range)
        for param_mapping in mappings
        for m_param, c_range in not_none(param_mapping).items()
    )

    solver.try_fulfill(And(*predicates), lock=False, allow_unknown=allow_not_deducible)


# public -------------------------------------------------------------------------------


def check_and_attach_candidates(
    candidates: list[tuple[Module, Component]],
    solver: Solver,
    allow_not_deducible: bool = False,
):
    """
    Check if given candidates are compatible with each other
    If so, attach them to the modules
    Raises:
        Contradiction
        NotCompatibleException
    """
    _check_candidates_compatible(candidates, solver, allow_not_deducible)

    for m, part in candidates:
        _attach(m, part)

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                f"Attached {part.lcsc_display} ('{part.description}') to "
                f"'{m.get_full_name(types=False)}'"
            )


def get_candidates(
    modules: Tree[Module], solver: Solver
) -> dict[Module, list[Component]]:
    candidates = modules.copy()
    parts = {}
    empty = set()

    while candidates:
        # TODO deduplicate parts with same literals
        new_parts = _find_modules(modules, solver)

        parts.update({m: p for m, p in new_parts.items() if p})
        empty = {m for m, p in new_parts.items() if not p}
        for m in parts:
            if m in candidates:
                candidates.pop(m)
        if not empty:
            return parts
        for m in empty:
            subtree = candidates.pop(m)
            if not subtree:
                raise PickError(
                    f"No candidates found for `{m}`:\n{m.pretty_params(solver)}", m
                )
            candidates.update(subtree)

    # should fail earlier
    return {}


def attach_single_no_check(cmp: Module, part: Component, solver: Solver):
    """
    Attach a single component to a module
    Attention: Does not check compatibility before or after!
    """
    _attach(cmp, part)
