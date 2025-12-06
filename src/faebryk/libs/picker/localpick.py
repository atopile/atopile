# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import pprint
from dataclasses import dataclass
from textwrap import indent
from typing import Callable, Iterable

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.solver.solver import Solver
from faebryk.core.solver.utils import Contradiction
from faebryk.libs.picker.picker import PickedPart, PickError
from faebryk.libs.util import not_none

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PickerOption:
    part: PickedPart
    params: dict[str, F.Literals.is_literal] | None = None
    """
    Parameters that need to be matched for this option to be valid.

    Assumes specified params are narrowest possible value for this part
    """
    filter: Callable[[fabll.Module], bool] | None = None
    pinmap: dict[str, F.Electrical] | None = None
    info: dict[str, str] | None = None

    def __hash__(self):
        return hash(self.part)


class PickErrorParams(PickError):
    def __init__(self, module: fabll.Node, options: list[PickerOption], solver: Solver):
        self.options = options

        MAX = 5

        options_str = "\n".join(
            f"{pprint.pformat(o.params, indent=4)}" for o in self.options[:MAX]
        )
        if len(self.options) > MAX:
            options_str += f"\n... and {len(self.options) - MAX} more"

        message = (
            f"Could not find part for {module}"
            f"\nwith params:\n{indent(module.pretty_params(solver), ' ' * 4)}"
            f"\nin options:\n {indent(options_str, ' ' * 4)}"
        )
        super().__init__(message, module)


def pick_module_by_params(
    module: fabll.Node, solver: Solver, options: Iterable[PickerOption]
):
    if module.has_trait(F.has_part_picked):
        logger.debug(f"Ignoring already picked module: {module}")
        return

    params = {
        not_none(p.get_parent())[1]: p.get_trait(F.Parameters.is_parameter)
        for p in module.get_children(
            direct_only=False,
            types=fabll.Node,
            required_trait=F.Parameters.is_parameter,
        )
    }

    filtered_options = [o for o in options if not o.filter or o.filter(module)]
    option: PickerOption | None = None
    contradictions = []

    for o in filtered_options:
        predicate_list: list[F.Expressions.is_assertable] = []

        for k, v in (o.params or {}).items():
            if not k.startswith("_"):
                param = params[k]
                predicate_list.append(
                    F.Expressions.Is.from_operands(
                        param.as_operand.get(),
                        v.as_operand.get(),
                    ).is_assertable.get()
                )

        # No predicates, thus always valid option
        if len(predicate_list) == 0:
            predicate = F.Expressions.Or.from_operands(
                F.Literals.make_simple_lit_singleton(
                    module.g, module.tg, True
                ).can_be_operand.get()
            )
            continue

        predicate = F.Expressions.And.from_operands(
            *[p.get_sibling_trait(F.Parameters.can_be_operand) for p in predicate_list]
        )
        try:
            solver.try_fulfill(predicate.is_assertable.get(), lock=True)
        except Contradiction as c:
            contradictions.append(c)
        else:
            option = o
            break

    if option is None:
        # TODO pass the contradictions
        raise PickErrorParams(module, list(options), solver)

    if option.pinmap:
        for pin_name, electrical in option.pinmap.items():
            lead_t = fabll.Traits.create_and_add_instance_to(
                node=electrical, trait=F.Lead.is_lead
            )
            fabll.Traits.create_and_add_instance_to(
                node=lead_t, trait=F.Lead.can_attach_to_pad_by_name
            ).setup(regex=f"{pin_name}")
    option.part.supplier.attach(module, option)
    fabll.Traits.create_and_add_instance_to(node=module, trait=F.has_part_picked).setup(
        option.part
    )

    logger.debug(f"Attached {option.part.partno} to {module}")
    return option
