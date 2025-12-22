"""
Assignment and trait overrides for the ato DSL compiler.

This module provides declarative specifications for converting legacy sugar syntax
and aliased trait names to their actual trait implementations.
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, ClassVar

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
        trait_class=F.has_explicit_part,
        expected_type=str,
        make_trait_field=lambda v: F.has_explicit_part.MakeChild(
            mfr=None,
            partno=None,
            supplier_id="lcsc",
            supplier_partno=v,
            pinmap=None,
            override_footprint=None,
        ),
    ),
    "mpn": TraitOverrideSpec(
        trait_class=F.has_explicit_part,
        expected_type=str,
        make_trait_field=lambda v: F.has_explicit_part.MakeChild(
            mfr=None,
            partno=v,
            supplier_id="lcsc",
            supplier_partno=None,
            pinmap=None,
            override_footprint=None,
        ),
    ),
    "manufacturer": TraitOverrideSpec(
        trait_class=F.has_explicit_part,
        expected_type=str,
        make_trait_field=lambda v: F.has_explicit_part.MakeChild(
            mfr=v,
            partno=None,
            supplier_id="lcsc",
            supplier_partno=None,
            pinmap=None,
            override_footprint=None,
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
        make_trait_field=lambda args: F.can_bridge.MakeEdge(
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
        trait_class=F.has_part_picked,
        make_trait_field=lambda args: F.has_part_picked.MakeChild(**args),
    ),
    "has_explicit_part": TraitOverrideSpec(
        trait_class=F.has_explicit_part,
        make_trait_field=lambda args: F.has_explicit_part.MakeChild(**args),
    ),
}

# Enum parameter overrides: handle string assignment to enum parameters
_ENUM_PARAMETER_OVERRIDES: dict[str, EnumParameterOverrideSpec] = {
    "temperature_coefficient": EnumParameterOverrideSpec(
        enum_type=F.Capacitor.TemperatureCoefficient,
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


class ConnectOverrideRegistry:
    """
    Registry of path translations for connect statements.

    Handles legacy path names that need to be translated to their current equivalents:
    - `vcc` -> `hv` (high voltage rail on ElectricPower)
    - `gnd` -> `lv` (low voltage rail on ElectricPower)

    This provides backwards compatibility for older ato code that used the legacy
    naming conventions for power interfaces.
    """

    # Mapping of legacy path segment names to their current equivalents
    PATH_TRANSLATIONS: ClassVar[dict[str, str]] = {
        "vcc": "hv",
        "gnd": "lv",
    }

    @classmethod
    def translate_segment(cls, segment: str) -> str:
        """Translate a single path segment if it's a legacy name."""
        if segment in cls.PATH_TRANSLATIONS:
            _deprecated_warning(segment, cls.PATH_TRANSLATIONS[segment])
            return cls.PATH_TRANSLATIONS[segment]
        return segment

    @classmethod
    def translate_identifiers(cls, identifiers: list[str]) -> list[str]:
        """Translate a list of string identifiers."""
        return [cls.translate_segment(s) for s in identifiers]

    @classmethod
    def translate_path(cls, path: LinkPath) -> LinkPath:
        """
        Translate any legacy path segments to their current equivalents.

        Only string segments are translated; EdgeTraversal objects are left unchanged.

        Args:
            path: A list of path segment identifiers (strings or EdgeTraversal)

        Returns:
            A new list with any legacy string names translated
        """
        return LinkPath(
            [
                cls.translate_segment(segment) if isinstance(segment, str) else segment
                for segment in path
            ]
        )
