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

    # Identifier for the literal child
    _LITERAL_CHILD_IDENTIFIER = "default_literal"
    _type_counter = 0

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
        # Create a concrete type with a unique name and the literal as a named child
        cls._type_counter += 1
        ConcreteType = fabll.Node._copy_type(
            cls, name=f"has_default_constraint_{cls._type_counter}"
        )

        # Add the literal as a named composition child
        ConcreteType._handle_cls_attr(cls._LITERAL_CHILD_IDENTIFIER, literal)

        return fabll._ChildField(ConcreteType)

    def get_default_literal(self) -> "F.Literals.is_literal | None":
        """Get the default literal value from this trait."""
        import faebryk.core.faebrykpy as fbrk

        # The literal is stored as a composition child with a known identifier
        child = fbrk.EdgeComposition.get_child_by_identifier(
            bound_node=self.instance,
            child_identifier=self._LITERAL_CHILD_IDENTIFIER,
        )
        if child is None:
            logger.warning(
                f"No child found with identifier {self._LITERAL_CHILD_IDENTIFIER}"
            )
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
        Check if the parameter has any explicit value constraints.

        We consider a constraint "explicit" if it's an IsSubset or Is predicate
        that constrains the parameter to a literal value (not just linking to
        another parameter).

        For example:
        - `param = 1A` → IsSubset(param, 1A) → explicit (has literal)
        - `assert param1 is param2` → Is(param1, param2) → NOT explicit (no literal)
        """
        from faebryk.library.Expressions import Is, IsSubset

        # Get the operatable trait via the implied trait accessor
        param_op = param.as_parameter_operatable.get()

        # Get all IsSubset predicates on this parameter
        subset_ops = param_op.get_operations(types=IsSubset, predicates_only=True)
        is_ops = param_op.get_operations(types=Is, predicates_only=True)

        logger.debug(
            f"Checking constraints on {param}: "
            f"IsSubset={len(subset_ops)}, Is={len(is_ops)}"
        )

        # Get the literal from our default trait for comparison
        my_literal = self.get_default_literal()
        logger.debug(f"Default literal: {my_literal}")
        if my_literal is None:
            logger.warning("No default literal found, falling back to constraint check")
            # No default literal stored, shouldn't happen but handle gracefully
            # Fall back to checking if any literal-involving constraint exists
            for op in subset_ops | is_ops:
                expr = op.get_trait(F.Expressions.is_expression)
                for operand in expr.get_operands():
                    if operand.as_literal.try_get() is not None:
                        return True
            return False

        for op in subset_ops | is_ops:
            # Get the expression and its operands
            expr = op.get_trait(F.Expressions.is_expression)
            operands = expr.get_operands()
            logger.debug(f"Examining constraint: {op}, operands: {operands}")

            # Find literals in this constraint
            has_bounded_literal = False
            is_our_literal = False
            literal_operand = None

            for operand in operands:
                if lit := operand.as_literal.try_get():
                    literal_operand = operand
                    # Check if this is our default literal
                    if lit.instance.node().is_same(other=my_literal.instance.node()):
                        is_our_literal = True
                        break

                    # Check if this is a bounded literal (not a domain constraint)
                    # Domain constraints like [0, ∞) are not "explicit" user values
                    lit_node = fabll.Traits(lit).get_obj_raw()
                    if numbers := lit_node.try_cast(F.Literals.Numbers):
                        # Check if bounds are finite - domain constraints have ∞
                        import math

                        min_val = numbers.get_min_value()
                        max_val = numbers.get_max_value()
                        if not math.isinf(min_val) and not math.isinf(max_val):
                            has_bounded_literal = True
                    else:
                        # Non-numeric literals (strings, bools) are always bounded
                        has_bounded_literal = True

            # Only count as explicit if it has a bounded literal AND it's not ours
            if has_bounded_literal and not is_our_literal:
                logger.debug(
                    f"Found explicit value constraint: {op}, literal: {literal_operand}"
                )
                return True

            logger.debug(
                f"Checked constraint {op}: has_bounded_literal={has_bounded_literal}, "
                f"is_our_literal={is_our_literal}"
            )

        return False

    @F.implements_design_check.register_post_design_verify_check
    def __check_post_design_verify__(self):
        """
        Apply default constraint if no explicit constraint exists.

        This runs in POST_DESIGN_VERIFY (earliest stage) so defaults are
        available for subsequent stages like Addressor offset resolution.
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
