# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import re
from dataclasses import fields
from enum import StrEnum
from socket import gaierror

import more_itertools

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from atopile.errors import UserInfraError
from faebryk.core import graph
from faebryk.core.solver.solver import LOG_PICK_SOLVE, Solver
from faebryk.libs.exceptions import UserException, downgrade
from faebryk.libs.http import RequestError, TimeoutException
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


def _from_smd_size(cls, size: SMDSize, type_node: graph.BoundNode) -> "BackendPackage":  # type: ignore[invalid-type-form]
    type_name = fbrk.TypeGraph.get_type_name(type_node=type_node)

    if type_name == F.Resistor._type_identifier():
        prefix = "R"
    elif type_name == F.Capacitor._type_identifier():
        prefix = "C"
    elif type_name == F.Inductor._type_identifier():
        prefix = "L"
    else:
        raise NotImplementedError(f"Unsupported pickable trait: {type_node}")

    try:
        return cls[f"{prefix}{size.imperial.without_prefix}"]
    except SMDSize.UnableToConvert:
        return cls[size.value]


BackendPackage.from_smd_size = classmethod(_from_smd_size)  # type: ignore


def _prepare_query(
    module: F.is_pickable, solver: Solver
) -> BaseParams | LCSCParams | ManufacturerPartParams:
    # assert module.has_trait(F.is_pickable)
    # Error can propagate through,
    # because we expect all pickable modules to be attachable
    module_node = module.get_pickable_node()
    check_attachable(module_node)

    if trait := module_node.try_get_trait(F.is_pickable_by_part_number):
        return ManufacturerPartParams(
            manufacturer_name=trait.get_manufacturer(),
            part_number=trait.get_partno(),
            quantity=qty,
        )

    elif trait := module_node.try_get_trait(F.is_pickable_by_supplier_id):
        if trait.get_supplier() == F.is_pickable_by_supplier_id.Supplier.LCSC.name:
            return LCSCParams(
                lcsc=_extract_numeric_id(trait.get_supplier_part_id()), quantity=qty
            )

    elif trait := module_node.try_get_trait(F.is_pickable_by_type):
        # TODO: Fix this
        params_t = make_params_for_type(module_node)

        if pkg_t := module_node.try_get_trait(F.has_package_requirements):
            package_constraint = solver.inspect_get_known_supersets(
                pkg_t.size.get().is_parameter.get()
            )
            package = (
                F.Literals.EnumsFactory(BackendPackage)  # type: ignore[arg-type]
                .bind_typegraph(tg=module.tg)
                .create_instance(g=module.g)
                .setup(
                    *[
                        BackendPackage.from_smd_size(SMDSize[s], trait.pick_type)  # type: ignore[attr-defined]
                        for s in F.Literals.AbstractEnums(
                            package_constraint.switch_cast().instance
                        ).get_values()
                    ]
                )
            )
        else:
            package = None

        generic_field_names = {f.name for f in fields(params_t)}
        _, known_params = more_itertools.partition(
            lambda p: p.get_name() in generic_field_names, (trait.get_params())
        )
        cmp_params = {
            p.get_name(): solver.inspect_get_known_supersets(
                p.get_trait(F.Parameters.is_parameter)
            )
            for p in known_params
        }
        if all(superset is None for superset in cmp_params.values()):
            logger.warning(f"Module `{module_node}` has no constrained parameters")

        return params_t(package=package, qty=qty, **cmp_params)  # type: ignore

    raise NotImplementedError(
        # f"Unsupported pickable trait: {module_node.get_trait(F.is_pickable)}"
        f"Unsupported pickable trait on node: {module_node}"
    )


def _process_candidates(
    module: F.is_pickable, candidates: list[Component]
) -> list[Component]:
    # Filter parts with weird pinmaps
    it = iter(candidates)
    filtered_candidates = []
    component_node = module.get_pickable_node()
    if not component_node.has_trait(F.Footprints.can_attach_to_footprint):
        raise PickError(
            f"Module {component_node.get_full_name(types=True)} does not have "
            "can_attach_to_footprint trait",
            component_node,
        )
    module_with_fp = component_node.get_trait(F.Footprints.can_attach_to_footprint)
    for c in it:
        try:
            attach(module_with_fp, c.lcsc_display, check_only=True, get_3d_model=False)
            filtered_candidates.append(c)
            # If we found one that's ok, just continue since likely enough
            filtered_candidates.extend(it)
            break
        except LCSC_NoDataException as ex:
            if len(candidates) == 1:
                raise PickError(
                    (
                        "LCSC has no footprint/symbol for any candidate for "
                        f"`{component_node}`. Loosen your selection criteria or try "
                        "another part which has an LCSC footprint and symbol."
                    ),
                    component_node,
                ) from ex
        except LCSC_PinmapException:
            # if all filtered by pinmap something is fishy
            if not filtered_candidates and candidates[-1] is c:
                raise

    return filtered_candidates


def _find_modules(
    modules: Tree[F.is_pickable], solver: Solver
) -> dict[F.is_pickable, list[Component]]:
    timings = Times(name="find_modules")

    params = {m: _prepare_query(m, solver) for m in modules}
    timings.add("prepare queries")

    grouped = groupby(params.items(), lambda p: p[1])
    queries = list(grouped.keys())

    def _map_response[T](results: list[T]) -> dict[F.is_pickable, T]:
        assert len(results) == len(queries)
        return {m: r for ms, r in zip(grouped.values(), results) for m, _ in ms}

    try:
        results = client.fetch_parts_multiple(queries)
        timings.add("fetch parts")
    except TimeoutException as e:
        raise UserInfraError(
            "Fetching component data failed to complete in time. "
            "Please try again later."
        ) from e
    except RequestError as e:
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

    out = {
        m: _process_candidates(module=m, candidates=r)
        for m, r in _map_response(results).items()
    }

    timings.add("process candidates")
    return out


def _attach(module: F.is_pickable, c: Component):
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
    module: fabll.Node, c: "Component", solver: Solver
) -> dict[F.Parameters.is_parameter, F.Literals.is_literal]:
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
        p.get_name(): p for p in module.get_trait(F.is_pickable_by_type).get_params()
    }
    component_params = c.attribute_literals(g=module.g, tg=module.tg)

    if no_attr := component_params.keys() - design_params:
        with downgrade(UserException):
            no_attr_str = "\n".join(f"- `{a}`" for a in no_attr)
            raise UserException(
                f"Module `{module}` is missing attributes:\n\n"
                f" {no_attr_str}\n\n"
                "This likely means you could use a more precise"
                " module/component in your design."
            )

    def _map_param(
        name: str, param: F.Parameters.is_parameter
    ) -> tuple[F.Parameters.is_parameter, F.Literals.is_literal]:
        c_range = component_params.get(name)
        if c_range is None:
            c_range = param.domain_set()
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
        if not c_range.is_subset_of(known_superset):
            if LOG_PICK_SOLVE:
                logger.warning(
                    f"Known superset {c_range} is not a subset of {known_superset}"
                    f" for part C{c.lcsc}"
                )
            raise NotCompatibleException(
                module, c, m_param.as_parameter_operatable.get(), c_range
            )

    return {p: c_range for p, c_range in param_mapping}


def _check_candidates_compatible(
    module_candidates: list[tuple[F.is_pickable, Component]],
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
        F.Expressions.Is.from_operands(
            m_param.as_operand.get(), c_range.as_operand.get()
        ).can_be_operand.get()
        for param_mapping in mappings
        for m_param, c_range in not_none(param_mapping).items()
    )

    solver.try_fulfill(
        F.Expressions.And.from_operands(*predicates).is_assertable.get(),
        lock=False,
        allow_unknown=allow_not_deducible,
    )


# public -------------------------------------------------------------------------------


def check_and_attach_candidates(
    candidates: list[tuple[F.is_pickable, Component]],
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
    modules: Tree[F.is_pickable], solver: Solver
) -> dict[F.is_pickable, list[Component]]:
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


def attach_single_no_check(cmp: F.is_pickable, part: Component, solver: Solver):
    """
    Attach a single component to a module
    Attention: Does not check compatibility before or after!
    """
    _attach(cmp, part)
