"""
Assignment and trait overrides for the ato DSL compiler.

This module provides declarative specifications for converting legacy sugar syntax
and aliased trait names to their actual trait implementations.

Reference overrides allow virtual fields that access trait-owned children,
such as `reference_shim` which resolves to the ElectricPower `reference` from
has_single_electric_reference.
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

import atopile.compiler.ast_types as AST
import faebryk.core.node as fabll
import faebryk.library._F as F
from atopile.compiler import DslException
from atopile.compiler.gentypegraph import (
    ActionsFactory,
    AddMakeChildAction,
    AddMakeLinkAction,
    FieldPath,
    LinkPath,
    NoOpAction,
)
from faebryk.core.faebrykpy import EdgeComposition, EdgeTrait
from faebryk.libs.exceptions import DeprecatedException, downgrade
from faebryk.libs.smd import SMDSize

logger = logging.getLogger(__name__)


def _deprecated_warning(input: str, replacement: str) -> None:
    with downgrade(DeprecatedException):
        raise DeprecatedException(
            f"'{input}' is deprecated. Use '{replacement}' instead."
        )


def _parse_smd_size(value: str) -> SMDSize:
    """
    Parse package string to SMDSize enum.

    Handles:
    - Prefixes like R0402, C0603, L0805 (strips prefix)
    - Imperial format like 0402 (adds I prefix)
    - Direct enum names like I0402
    """
    value = re.sub(r"^[RCL]", "I", value)

    if re.match(r"^[0-9]+$", value):
        value = f"I{value}"

    valid_names = {s.name for s in SMDSize}
    if value not in valid_names:
        from faebryk.libs.util import md_list

        raise DslException(
            f"Invalid package: `{value}`. Valid packages are:\n"
            f"{md_list(s.name for s in SMDSize)}"
        )

    return SMDSize[value]


@dataclass
class TraitOverrideSpec:
    """Specification for creating a trait from an assignment or trait statement."""

    trait_class: type[fabll.Node]
    make_trait_field: Callable[[Any], fabll._ChildField] | None = None
    expected_type: type | None = None
    skip_value: Callable[[Any], bool] | None = None
    transform_value: Callable[[Any], Any] | None = None
    deprecated_hint: str | None = None


@dataclass
class EnumParameterOverrideSpec:
    """Specification for constraining an enum parameter from a string assignment."""

    enum_type: type[Enum]


def _get_enum_member(enum_type: type[Enum], value: str) -> Enum:
    """Get enum member from string, with helpful error message."""
    try:
        return enum_type[value]
    except KeyError:
        valid = [e.name for e in enum_type]
        raise DslException(
            f"Invalid value: '{value}'. Valid values: {', '.join(valid)}"
        )


_ASSIGNMENT_OVERRIDES: dict[str, TraitOverrideSpec] = {
    "required": TraitOverrideSpec(
        trait_class=F.requires_external_usage,
        expected_type=bool,
        skip_value=lambda v: not v,
    ),
    "package": TraitOverrideSpec(
        trait_class=F.has_package_requirements,
        expected_type=str,
        transform_value=_parse_smd_size,
        make_trait_field=lambda size: F.has_package_requirements.MakeChild(size=size),
    ),
    "lcsc_id": TraitOverrideSpec(
        trait_class=F.Pickable.is_pickable_by_supplier_id,
        expected_type=str,
        make_trait_field=lambda v: F.Pickable.is_pickable_by_supplier_id.MakeChild(
            supplier_part_id=v
        ),
    ),
    "mpn": TraitOverrideSpec(
        trait_class=F.Pickable.has_mpn_assigned,
        expected_type=str,
        make_trait_field=lambda v: F.Pickable.has_mpn_assigned.MakeChild(
            mpn=v,
        ),
    ),
    "manufacturer": TraitOverrideSpec(
        trait_class=F.Pickable.has_mfr_assigned,
        expected_type=str,
        make_trait_field=lambda v: F.Pickable.has_mfr_assigned.MakeChild(
            mfr=v,
        ),
    ),
    "datasheet_url": TraitOverrideSpec(
        trait_class=F.has_datasheet,
        expected_type=str,
        make_trait_field=lambda v: F.has_datasheet.MakeChild(datasheet=v),
    ),
    "designator_prefix": TraitOverrideSpec(
        trait_class=F.has_designator_prefix,
        expected_type=str,
        make_trait_field=lambda v: F.has_designator_prefix.MakeChild(prefix=v),
    ),
    "override_net_name": TraitOverrideSpec(
        trait_class=F.has_net_name_suggestion,
        expected_type=str,
        make_trait_field=lambda v: F.has_net_name_suggestion.MakeChild(
            name=v, level=F.has_net_name_suggestion.Level.EXPECTED
        ),
    ),
    "suggest_net_name": TraitOverrideSpec(
        trait_class=F.has_net_name_suggestion,
        expected_type=str,
        make_trait_field=lambda v: F.has_net_name_suggestion.MakeChild(
            name=v, level=F.has_net_name_suggestion.Level.SUGGESTED
        ),
    ),
}

_TRAIT_OVERRIDES: dict[str, TraitOverrideSpec] = {
    "can_bridge_by_name": TraitOverrideSpec(
        trait_class=F.can_bridge,
        make_trait_field=lambda args: F.can_bridge.MakeChild(
            [args.get("input_name", "input")],
            [args.get("output_name", "output")],
        ),
        deprecated_hint="Use can_bridge instead",
    ),
    "has_datasheet_defined": TraitOverrideSpec(
        trait_class=F.has_datasheet,
        make_trait_field=lambda args: F.has_datasheet.MakeChild(
            datasheet=args["datasheet"]
        ),
        deprecated_hint="Use has_datasheet instead",
    ),
    "has_single_electric_reference_shared": TraitOverrideSpec(
        trait_class=F.has_single_electric_reference,
        make_trait_field=lambda args: F.has_single_electric_reference.MakeChild(
            ground_only=args.get("gnd_only", False)
        ),
        deprecated_hint="Use has_single_electric_reference instead",
    ),
    "has_part_picked": TraitOverrideSpec(
        trait_class=F.Pickable.has_part_picked,
        make_trait_field=lambda args: F.Pickable.has_part_picked.MakeChild(**args),
    ),
}

# Enum parameter overrides: handle string assignment to enum parameters
_ENUM_PARAMETER_OVERRIDES: dict[str, EnumParameterOverrideSpec] = {
    "temperature_coefficient": EnumParameterOverrideSpec(
        enum_type=F.Capacitor.TemperatureCoefficient,
    ),
    "channel_type": EnumParameterOverrideSpec(
        enum_type=F.MOSFET.ChannelType,
    ),
    "saturation_type": EnumParameterOverrideSpec(
        enum_type=F.MOSFET.SaturationType,
    ),
    "doping_type": EnumParameterOverrideSpec(
        enum_type=F.BJT.DopingType,
    ),
    "operation_region": EnumParameterOverrideSpec(
        enum_type=F.BJT.OperationRegion,
    ),
    "fuse_type": EnumParameterOverrideSpec(
        enum_type=F.Fuse.FuseType,
    ),
    "response_type": EnumParameterOverrideSpec(
        enum_type=F.Fuse.ResponseType,
    ),
}


class TraitOverrideRegistry:
    """
    Registry for trait overrides from both assignment and trait statements.

    Assignment overrides handle legacy sugar like:
    - `power.required = True` -> requires_external_usage trait
    - `cap.package = "0402"` -> has_package_requirements trait

    Trait overrides handle legacy/aliased trait names:
    - `trait can_bridge_by_name<...>` -> can_bridge trait
    """

    @classmethod
    def _apply_spec(
        cls,
        spec: TraitOverrideSpec,
        name: str,
        target_path: LinkPath | None,
        value: Any,
    ) -> list[AddMakeChildAction | AddMakeLinkAction] | NoOpAction:
        """Apply a spec to create trait actions."""
        if spec.deprecated_hint:
            _deprecated_warning(name, spec.trait_class.__name__)

        if spec.expected_type and not isinstance(value, spec.expected_type):
            raise DslException(
                f"Invalid value for `{name}`: expected "
                f"{spec.expected_type.__name__}, got {type(value).__name__}"
            )

        if spec.skip_value and spec.skip_value(value):
            return NoOpAction()

        final_value = spec.transform_value(value) if spec.transform_value else value

        try:
            trait_field = (
                spec.make_trait_field(final_value)
                if spec.make_trait_field
                else spec.trait_class.MakeChild()
            )
        except KeyError as e:
            raise DslException(f"Missing value for `{name}`: {e}") from e

        return ActionsFactory.trait_from_field(trait_field, target_path)

    @classmethod
    def handle_assignment(
        cls, target_path: FieldPath, assignable_node: AST.Assignable
    ) -> list[AddMakeChildAction | AddMakeLinkAction] | NoOpAction:
        """Handle assignment overrides like `node.package = "0402"`."""
        leaf_name = target_path.leaf.identifier
        spec = _ASSIGNMENT_OVERRIDES[leaf_name]
        value_node = assignable_node.get_value().switch_cast()

        if spec.expected_type is str and value_node.isinstance(AST.AstString):
            value = value_node.cast(t=AST.AstString).get_text()
        elif spec.expected_type is bool and value_node.isinstance(AST.Boolean):
            value = value_node.cast(t=AST.Boolean).get_value()
        else:
            expected_type_name = {str: "string", bool: "boolean"}[spec.expected_type]

            raise DslException(
                f"Invalid value for `{leaf_name}`: expected "
                f"{expected_type_name}, got {type(value_node).__name__}"
            )

        parent_path: LinkPath | None = (
            list(FieldPath(segments=tuple(target_path.parent_segments)).identifiers())
            if target_path.parent_segments
            else None
        )

        return cls._apply_spec(spec, leaf_name, parent_path, value)

    @classmethod
    def handle_trait(
        cls,
        trait_type_name: str,
        target_path: LinkPath,
        template_args: dict[str, Any] | None,
    ) -> list[AddMakeChildAction | AddMakeLinkAction] | NoOpAction:
        """Handle trait overrides like `trait can_bridge_by_name<...>`."""
        return cls._apply_spec(
            _TRAIT_OVERRIDES[trait_type_name],
            trait_type_name,
            target_path,
            template_args or {},
        )

    @classmethod
    def handle_enum_parameter_assignment(
        cls,
        target_path: FieldPath,
        assignable_node: AST.Assignable,
        constraint_expr: type[fabll.Node] | None = None,
    ) -> list[AddMakeChildAction]:
        """Handle enum parameter assignments like `cap.temperature_coefficient`."""
        leaf_name = target_path.leaf.identifier
        spec = _ENUM_PARAMETER_OVERRIDES[leaf_name]
        value_node = assignable_node.get_value().switch_cast()

        if not value_node.isinstance(AST.AstString):
            raise DslException(
                f"Invalid value for `{leaf_name}`: expected string, "
                f"got {type(value_node).__name__}"
            )

        string_value = value_node.cast(t=AST.AstString).get_text()
        enum_value = _get_enum_member(spec.enum_type, string_value)

        # Create enum literal (parameter_actions will create the constraint)
        enum_literal = F.Literals.AbstractEnums.MakeChild(enum_value)

        return ActionsFactory.parameter_actions(
            target_path=target_path,
            param_child=None,
            constraint_operand=enum_literal,
            constraint_expr=constraint_expr,
        )

    @classmethod
    def handle_default_assignment(
        cls,
        target_path: FieldPath,
        literal_field: fabll._ChildField,
    ) -> list[AddMakeChildAction | AddMakeLinkAction]:
        """
        Handle default value assignment like `param.default = 1A`.

        Creates a has_default_constraint trait attached to the parent parameter.
        The default value is only applied if no explicit constraint exists.

        Args:
            target_path: Full path including ".default" (e.g., "max_current.default")
            literal_field: The literal value _ChildField from visiting the assignable

        Returns:
            Actions to create the trait and link it to the parameter
        """
        if not target_path.parent_segments:
            raise DslException(
                "`.default` must be used on a parameter field, "
                "e.g., `param.default = 1A`"
            )

        # Get the parent path (the parameter we're attaching the default to)
        parent_path: LinkPath = list(
            FieldPath(segments=tuple(target_path.parent_segments)).identifiers()
        )

        # Create the has_default_constraint trait with the literal
        trait_field = F.has_default_constraint.MakeChild(literal=literal_field)

        return ActionsFactory.trait_from_field(trait_field, parent_path)

    @classmethod
    def matches_default_override(
        cls, name: str, assignable_node: AST.Assignable
    ) -> bool:
        """Check if this is a `.default` assignment."""
        if assignable_node.get_value().switch_cast().isinstance(AST.NewExpression):
            return False
        if assignable_node.get_value().switch_cast().isinstance(AST.AstString):
            return False
        if assignable_node.get_value().switch_cast().isinstance(AST.Boolean):
            return False

        return name == "default"

    @classmethod
    def matches_assignment_override(
        cls, name: str, assignable_node: AST.Assignable
    ) -> bool:
        if assignable_node.get_value().switch_cast().isinstance(AST.NewExpression):
            return False

        return name in _ASSIGNMENT_OVERRIDES

    @classmethod
    def matches_enum_parameter_override(
        cls, name: str, assignable_node: AST.Assignable
    ) -> bool:
        if assignable_node.get_value().switch_cast().isinstance(AST.NewExpression):
            return False

        return name in _ENUM_PARAMETER_OVERRIDES

    @classmethod
    def matches_trait_override(cls, name: str) -> bool:
        return name in _TRAIT_OVERRIDES


@dataclass
class ReferenceOverrideSpec:
    """
    Specification for transforming a field reference into a trait child access.

    When a field path ends with the specified name (e.g., `reference_shim`),
    the path is transformed to traverse through the specified trait and access
    its child.

    For example, `i2c.reference_shim` becomes:
        ["i2c", EdgeTrait(has_single_electric_reference),
         EdgeComposition("reference")]
    """

    trait_class: type[fabll.Node]
    child_name: str


# Reference overrides: virtual fields that access trait-owned children
_REFERENCE_OVERRIDES: dict[str, ReferenceOverrideSpec] = {
    "reference_shim": ReferenceOverrideSpec(
        trait_class=F.has_single_electric_reference,
        child_name="reference",
    ),
}

# Trait pointer overrides: treat a path segment as a trait traversal rather than
# a composition child. This allows ato to access trait-owned children using:
#
#     has_single_electric_reference.reference ~ power_io
#
# i.e. `has_single_electric_reference` acts like a pointer to the trait instance
# on the current node (or a nested node if used mid-path).
_TRAIT_POINTER_OVERRIDES: dict[str, type[fabll.Node]] = {
    "has_single_electric_reference": F.has_single_electric_reference,
}


class ReferenceOverrideRegistry:
    """
    Registry for reference overrides that transform field paths into trait lookups.

    Reference overrides handle virtual fields like `reference_shim` which resolve
    to a child of a trait. When `i2c.reference_shim` is used in a connection, it's
    transformed to traverse the `has_single_electric_reference` trait and access
    its `reference` child to get the actual ElectricPower.

    This allows connections like `i2c.reference_shim ~ power` to work on any module
    that has the `has_single_electric_reference` trait, without requiring an explicit
    `reference_shim` field to be defined.

    Also handles suffixes like `i2c.reference_shim.hv` by keeping the suffix after
    the trait/reference expansion.
    """

    @classmethod
    def transform_link_path(cls, path: LinkPath) -> LinkPath:
        """
        Transform a LinkPath if it contains a reference override identifier.

        Currently supports:
        - `reference_shim`: resolves to ElectricPower from has_single_electric_reference

        Handles both terminal usage (i2c.reference_shim) and suffixed usage
        (i2c.reference_shim.hv).

        Args:
            path: The original LinkPath (list of string identifiers or EdgeTraversal)

        Returns:
            Transformed LinkPath with trait traversal, or original path if no match
        """
        if not path:
            return path

        # First: trait pointer overrides
        # (e.g. `has_single_electric_reference.reference`)
        for i, element in enumerate(path):
            if not isinstance(element, str):
                continue
            if element not in _TRAIT_POINTER_OVERRIDES:
                continue
            trait_type = _TRAIT_POINTER_OVERRIDES[element]
            prefix = list(path[:i])
            suffix = list(path[i + 1 :])
            return [
                *prefix,
                EdgeTrait.traverse(trait_type=trait_type),
                *suffix,
            ]

        # Scan through path looking for reference override identifiers
        for i, element in enumerate(path):
            if not isinstance(element, str):
                continue

            if element not in _REFERENCE_OVERRIDES:
                continue

            spec = _REFERENCE_OVERRIDES[element]

            # Deprecation: reference_shim -> has_single_electric_reference.reference
            #
            # We keep `reference_shim` for now for backwards-compatibility, but it
            # should be replaced with explicit trait-pointer syntax.
            if element == "reference_shim":
                prefix = list(path[:i])
                suffix = list(path[i + 1 :])

                def _fmt(parts: list[str]) -> str:
                    return ".".join(parts) if parts else "<self>"

                prefix_str = [p for p in prefix if isinstance(p, str)]
                suffix_str = [s for s in suffix if isinstance(s, str)]

                old_expr = _fmt([*prefix_str, "reference_shim", *suffix_str])
                replacement_parts = [
                    *prefix_str,
                    "has_single_electric_reference",
                    "reference",
                    *suffix_str,
                ]
                with downgrade(DeprecatedException):
                    raise DeprecatedException(
                        "Field `reference_shim` is deprecated.\n\n"
                        f"Replace `{old_expr}` with `{_fmt(replacement_parts)}`.\n\n"
                        "Example:\n"
                        "- `i2c.reference_shim ~ power`\n"
                        "- `i2c.has_single_electric_reference.reference ~ power`"
                    )

            # Build the new path:
            # - prefix: everything before the override identifier
            # - middle: trait traversal + child access
            # - suffix: everything after the override identifier
            #
            # Original: ["i2c", "reference_shim", "hv"]
            # Becomes: ["i2c", EdgeTrait(trait), EdgeComposition("reference"), "hv"]
            prefix = list(path[:i])
            suffix = list(path[i + 1 :])
            return [
                *prefix,
                EdgeTrait.traverse(trait_type=spec.trait_class),
                EdgeComposition.traverse(identifier=spec.child_name),
                *suffix,
            ]

        return path
