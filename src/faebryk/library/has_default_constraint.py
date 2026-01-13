# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
Trait for marking parameters with default values that can be overridden.

When a parameter has this trait, the default value only applies if no explicit
constraint is set by the user. This enables package authors to provide sensible
defaults while allowing users to override them without causing contradictions.

Example in ato:
    # Package definition
    max_current.default = 1A  # Will apply only if user doesn't constrain

    # User code
    device.max_current = 500mA  # Overrides the default, no contradiction

The trait registers a POST_DESIGN check that:
1. Examines the parameter for explicit IsSubset/Is constraints
2. If found: does nothing (user's constraint takes precedence)
3. If not found: creates an IsSubset constraint from the default value
"""

import logging
from typing import Self

import faebryk.core.node as fabll
import faebryk.library._F as F

logger = logging.getLogger(__name__)


class has_default_constraint(fabll.Node):
    """
    Marks a parameter with a default constraint value.

    The default is only applied if no explicit constraint exists on the parameter.
    This allows package authors to set defaults that users can override without
    causing ContradictionByLiteral errors.

    Works with any literal type: Numbers, Strings, Booleans, Enums.
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    # Design check trait for pre-solve default application
    design_check = fabll.Traits.MakeEdge(F.implements_design_check.MakeChild())

    @classmethod
    def MakeChild(
        cls, literal: "fabll._ChildField[F.Literals.is_literal]"
    ) -> fabll._ChildField[Self]:
        """
        Create a has_default_constraint child field with the specified default literal.

        Args:
            literal: The literal value _ChildField from the parser
                     (e.g., 1A, 10kohm +/- 5%, "string", True)
        """
        out: fabll._ChildField[Self] = fabll._ChildField(cls)

        # Add the literal as a dependant with a known identifier so we can find it later
        out.add_dependant(literal, identifier="default_literal")

        return out

    def get_default_literal(self) -> "F.Literals.is_literal | None":
        """Get the default literal value from this trait."""
        import faebryk.core.faebrykpy as fbrk

        # The literal is stored as a child with identifier "default_literal"
        child = fbrk.EdgeComposition.get_child_by_identifier(
            bound_node=self.instance,
            child_identifier="default_literal",
        )
        if child is None:
            return None

        # Get the is_literal trait from the child
        child_node = fabll.Node.bind_instance(child)
        return child_node.try_get_trait(F.Literals.is_literal)

    def _get_target_parameter(self) -> "F.Parameters.is_parameter | None":
        """
        Get the parameter this default constraint is attached to.

        The trait is attached to a parameter via EdgeTrait, so we traverse
        back to find the parameter.
        """
        # Get the object this trait is attached to
        owner = fabll.Traits(self).get_obj_raw()

        # Check if owner has is_parameter trait (it's a parameter)
        if param := owner.try_get_trait(F.Parameters.is_parameter):
            return param

        return None

    def _has_explicit_constraint(self, param: "F.Parameters.is_parameter") -> bool:
        """
        Check if the parameter has any explicit IsSubset or Is constraints.

        We consider a constraint "explicit" if it's an IsSubset or Is predicate
        that wasn't created by this default trait.
        """
        from faebryk.library.Expressions import Is, IsSubset

        # Get the operatable trait via the implied trait accessor
        param_op = param.as_parameter_operatable.get()

        # Get all IsSubset predicates on this parameter
        subset_ops = param_op.get_operations(types=IsSubset, predicates_only=True)
        is_ops = param_op.get_operations(types=Is, predicates_only=True)

        # Get the literal from our default trait for comparison
        my_literal = self.get_default_literal()
        if my_literal is None:
            # No default literal stored, shouldn't happen but handle gracefully
            return len(subset_ops) > 0 or len(is_ops) > 0

        for op in subset_ops | is_ops:
            # Get the expression and its operands
            expr = op.get_trait(F.Expressions.is_expression)
            operands = expr.get_operands()

            # Check if this constraint uses our default literal
            is_our_constraint = False
            for operand in operands:
                if lit := operand.as_literal.try_get():
                    # Compare if this is our literal by checking if it's the same node
                    if lit.instance.node().is_same(my_literal.instance.node()):
                        is_our_constraint = True
                        break

            if not is_our_constraint:
                # Found an explicit constraint that's not from our default
                logger.debug(
                    f"Found explicit constraint on parameter, skipping default: {op}"
                )
                return True

        return False

    @F.implements_design_check.register_post_design_check
    def __check_post_design__(self):
        """
        Apply default constraint if no explicit constraint exists.

        This runs before the solver, allowing default values to be set up
        only when the user hasn't provided their own constraints.
        """
        param = self._get_target_parameter()
        if param is None:
            logger.warning(
                f"has_default_constraint trait attached to non-parameter: {self}"
            )
            return

        # Check if there's an explicit constraint
        if self._has_explicit_constraint(param):
            logger.info(
                f"Parameter has explicit constraint, skipping default for: {param}"
            )
            return

        # No explicit constraint found - apply the default
        logger.info(f"Applying default constraint to parameter: {param}")

        # Create IsSubset constraint: param ⊆ default_literal
        from faebryk.library.Expressions import IsSubset

        default_lit = self.get_default_literal()
        if default_lit is None:
            logger.warning(f"No default literal found for: {self}")
            return

        param_op = param.as_operand.get()
        lit_op = default_lit.as_operand.get()

        # Create and assert the IsSubset constraint
        IsSubset.bind_typegraph(tg=self.tg).create_instance(g=self.g).setup(
            subset=param_op,
            superset=lit_op,
            assert_=True,
        )
