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
from faebryk.core.solver.solver import Solver
from faebryk.core.solver.utils import LOG_PICK_SOLVE
from faebryk.libs.http import RequestError
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
)
from faebryk.libs.picker.picker import PickError
from faebryk.libs.smd import SMDSize
from faebryk.libs.test.times import Times
from faebryk.libs.util import (
    Tree,
    cast_assert,
    groupby,
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
    module: F.Pickable.is_pickable,
    solver: Solver,
    g: graph.GraphView,
    tg: fbrk.TypeGraph,
) -> BaseParams | LCSCParams | ManufacturerPartParams:
    # assert module.has_trait(F.Pickable.is_pickable)
    # Error can propagate through,
    # because we expect all pickable modules to be attachable
    module_node = module.get_pickable_node()
    check_attachable(module_node)

    if trait := module_node.try_get_trait(F.Pickable.is_pickable_by_part_number):
        return ManufacturerPartParams(
            manufacturer_name=trait.get_manufacturer(),
            part_number=trait.get_partno(),
            quantity=qty,
        )

    elif trait := module_node.try_get_trait(F.Pickable.is_pickable_by_supplier_id):
        if (
            trait.get_supplier()
            == F.Pickable.is_pickable_by_supplier_id.Supplier.LCSC.name
        ):
            return LCSCParams(
                lcsc=_extract_numeric_id(trait.get_supplier_part_id()), quantity=qty
            )

    elif trait := module_node.try_get_trait(F.Pickable.is_pickable_by_type):
        # TODO: Fix this
        params_t = make_params_for_type(module_node)

        if pkg_t := module_node.try_get_trait(F.has_package_requirements):
            package_constraint = pkg_t.size.get().try_extract_superset()
            if package_constraint is None:
                raise PickError(
                    f"Module `{module_node}` has no constrained package requirements",
                    module_node,
                )
            package = (
                F.Literals.EnumsFactory(BackendPackage)  # type: ignore[arg-type]
                .bind_typegraph(tg=tg)
                .create_instance(g=g)
                .setup(
                    *[
                        BackendPackage.from_smd_size(SMDSize[s], trait.pick_type)  # type: ignore[attr-defined]
                        for s in F.Literals.AbstractEnums(
                            package_constraint.instance
                        ).get_names()
                    ]
                )
            )
        else:
            package = None

        generic_field_names = {f.name for f in fields(params_t)}
        _, known_params = more_itertools.partition(
            lambda p: fabll.Traits(p).get_obj_raw().get_name() in generic_field_names,
            trait.get_params(),
        )
        cmp_params = {
            fabll.Traits(p).get_obj_raw(): solver.extract_superset(
                # FIXME g
                p  # , g=g, tg=tg
            )
            for p in known_params
        }
        if all(superset is None for superset in cmp_params.values()):
            logger.warning(f"Module `{module_node}` has no constrained parameters")

        # TODO: More robust validation against API contract
        # Check for singleton literals
        for param, is_lit in cmp_params.items():
            literal_node = is_lit.switch_cast()
            if literal_node.isinstance(F.Literals.Numbers):
                if literal_node.is_singleton():
                    from atopile.compiler import DslRichException, DslValueError

                    raise DslRichException(
                        message=(
                            f"Parameter `{param.pretty_repr()}` is assigned to an "
                            f"exact value ({literal_node.pretty_str()}) "
                            "instead of being constrained to an interval. "
                        ),
                        original=DslValueError(),
                    )

        return params_t(
            package=package, qty=qty, **{k.get_name(): v for k, v in cmp_params.items()}
        )  # type: ignore

    raise NotImplementedError(
        # f"Unsupported pickable trait: {module_node.get_trait(F.Pickable.is_pickable)}"
        f"Unsupported pickable trait on node: {module_node}"
    )


def _process_candidates(
    module: F.Pickable.is_pickable, candidates: list[Component]
) -> list[Component]:
    timings = Times(name="process_candidates")

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
    timings.add("setup")

    for idx, c in enumerate(it):
        try:
            with timings.measure(f"attach_check_{idx}"):
                attach(
                    module_with_fp, c.lcsc_display, check_only=True, get_3d_model=False
                )
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

    timings.add("filter_done")
    return filtered_candidates


def _find_modules(
    modules: Tree[F.Pickable.is_pickable], solver: Solver
) -> dict[F.Pickable.is_pickable, list[Component]]:
    timings = Times(name="find_modules")

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    params = {m: _prepare_query(m, solver, g, tg) for m in modules}
    timings.add("prepare queries")

    # deduplicate params
    grouped = groupby(params.items(), lambda p: str(p[1].serialize()))
    queries = [v[0][1] for v in grouped.values()]
    logger.debug(f"Queries: {len(queries)}")

    def _map_response[T](results: list[T]) -> dict[F.Pickable.is_pickable, T]:
        assert len(results) == len(queries)
        return {m: r for ms, r in zip(grouped.values(), results) for m, _ in ms}

    try:
        results = client.fetch_parts_multiple(queries)
        timings.add("fetch parts")
        logger.debug(
            f"Fetched {len(results)} parts in {timings.get_formatted('fetch parts')}"
        )
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
    logger.debug(
        f"Processed {len(out)} candidates in "
        f"{timings.get_formatted('process candidates')}"
    )
    return out


def _attach(module: F.Pickable.is_pickable, c: Component):
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


# public -------------------------------------------------------------------------------


def get_candidates(
    modules: Tree[F.Pickable.is_pickable], solver: Solver
) -> dict[F.Pickable.is_pickable, list[Component]]:
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


def attach_single_no_check(
    cmp: F.Pickable.is_pickable, part: Component, solver: Solver
):
    """
    Attach a single component to a module
    Attention: Does not check compatibility before or after!
    """
    _attach(cmp, part)
