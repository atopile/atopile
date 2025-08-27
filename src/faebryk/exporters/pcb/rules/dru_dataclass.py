"""KiCad DRU (Design Rules) file format dataclasses for proper SEXP serialization."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from faebryk.libs.sexp.dataclass_sexp import SEXP_File, sexp_field

# Fix for forward reference type checking
if TYPE_CHECKING:
    from typing import Any


@dataclass
class C_kicad_dru_file(SEXP_File):
    """Represents a KiCad DRU (Design Rules) file.

    The file structure is:
    (version 1)
    (rule rule_name
      (layer "layer_name")
      (constraint constraint_type (min value) (opt value) (max value))
      (condition "expression")
    )
    ...
    """

    @dataclass
    class C_kicad_dru:
        """The root element containing version and rules."""

        @dataclass
        class C_value:
            """A value with unit (e.g., 0.2mm)."""

            value: float = field(**sexp_field(positional=True))
            unit: str = field(**sexp_field(positional=True))

            def __str__(self):
                return f"{self.value:.2f}{self.unit}"

        @dataclass
        class C_rule:
            """A single design rule."""

            name: str = field(**sexp_field(positional=True))
            layer: Optional[str] = None
            constraints: list[C_constraint] = field(default_factory=list)
            condition: Optional[str] = None

            @dataclass
            class C_constraint:
                """Base class for constraints - will be specialized for each type."""

                pass

            @dataclass
            class C_track_width(C_constraint):
                """Track width constraint."""

                _name: str = field(default="track_width", **sexp_field(positional=True))
                min: Optional[C_kicad_dru_file.C_kicad_dru.C_value] = None
                opt: Optional[C_kicad_dru_file.C_kicad_dru.C_value] = None
                max: Optional[C_kicad_dru_file.C_kicad_dru.C_value] = None

            @dataclass
            class C_diff_pair_gap(C_constraint):
                """Differential pair gap constraint."""

                _name: str = field(
                    default="diff_pair_gap", **sexp_field(positional=True)
                )
                min: Optional[C_kicad_dru_file.C_kicad_dru.C_value] = None
                opt: Optional[C_kicad_dru_file.C_kicad_dru.C_value] = None
                max: Optional[C_kicad_dru_file.C_kicad_dru.C_value] = None

            @dataclass
            class C_clearance(C_constraint):
                """Clearance constraint."""

                _name: str = field(default="clearance", **sexp_field(positional=True))
                min: Optional[C_kicad_dru_file.C_kicad_dru.C_value] = None

        version: int = field(**sexp_field(positional=True), default=1)
        rules: list[C_rule] = field(**sexp_field(multidict=True), default_factory=list)

    kicad_dru: C_kicad_dru = field(default_factory=C_kicad_dru)


def format_mm(value: float) -> str:
    """Format a value in millimeters for KiCad."""
    return f"{value:.2f}mm"


def create_track_width_rule(
    name: str,
    layer: str,
    min_mm: Optional[float] = None,
    opt_mm: Optional[float] = None,
    max_mm: Optional[float] = None,
    condition: Optional[str] = None,
) -> C_kicad_dru_file.C_kicad_dru.C_rule:
    """Create a track width rule."""
    rule = C_kicad_dru_file.C_kicad_dru.C_rule(
        name=name,
        layer=layer,
        condition=condition,
    )

    constraint = C_kicad_dru_file.C_kicad_dru.C_rule.C_track_width()
    if min_mm is not None:
        constraint.min = C_kicad_dru_file.C_kicad_dru.C_value(min_mm, "mm")
    if opt_mm is not None:
        constraint.opt = C_kicad_dru_file.C_kicad_dru.C_value(opt_mm, "mm")
    if max_mm is not None:
        constraint.max = C_kicad_dru_file.C_kicad_dru.C_value(max_mm, "mm")

    rule.constraints.append(constraint)
    return rule


def create_diff_pair_rule(
    name: str,
    layer: str,
    track_width_opt_mm: float,
    gap_opt_mm: float,
    condition: str = "A.inDiffPair('*')",
) -> C_kicad_dru_file.C_kicad_dru.C_rule:
    """Create a differential pair rule with track width and gap constraints."""
    rule = C_kicad_dru_file.C_kicad_dru.C_rule(
        name=name,
        layer=layer,
        condition=condition,
    )

    # Add track width constraint
    tw_constraint = C_kicad_dru_file.C_kicad_dru.C_rule.C_track_width()
    tw_constraint.opt = C_kicad_dru_file.C_kicad_dru.C_value(track_width_opt_mm, "mm")
    rule.constraints.append(tw_constraint)

    # Add diff pair gap constraint
    gap_constraint = C_kicad_dru_file.C_kicad_dru.C_rule.C_diff_pair_gap()
    gap_constraint.opt = C_kicad_dru_file.C_kicad_dru.C_value(gap_opt_mm, "mm")
    rule.constraints.append(gap_constraint)

    return rule
