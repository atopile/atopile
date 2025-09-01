"""
Build faebryk core objects from ato DSL.
"""

import inspect
import itertools
import json
import logging
import operator
import os
import typing
from collections import defaultdict
from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum, StrEnum
from itertools import chain, pairwise
from pathlib import Path
from types import UnionType
from typing import (
    Any,
    Iterable,
    Literal,
    Sequence,
    Type,
    Union,
    cast,
)

from antlr4 import ParserRuleContext
from more_itertools import last
from pint import UndefinedUnitError

import faebryk.library._F as F
import faebryk.libs.library.L as L
from atopile import address, errors
from atopile.attributes import GlobalAttributes, _has_ato_cmp_attrs, shim_map
from atopile.config import config, find_project_dir
from atopile.datatypes import (
    FieldRef,
    KeyOptItem,
    KeyOptMap,
    KeyType,
    ReferencePartType,
    StackList,
    TypeRef,
    is_int,
)
from atopile.parse import parser
from atopile.parse_utils import get_src_info_from_ctx
from atopile.parser.AtoParser import AtoParser as ap
from atopile.parser.AtoParserVisitor import AtoParserVisitor
from faebryk.core.node import FieldExistsError, NodeException
from faebryk.core.parameter import (
    Arithmetic,
    ConstrainableExpression,
    GreaterOrEqual,
    Is,
    IsSubset,
    LessOrEqual,
    Max,
    Min,
    Parameter,
)
from faebryk.core.trait import Trait, TraitImpl
from faebryk.libs.exceptions import accumulate, downgrade, iter_through_errors
from faebryk.libs.library.L import Range, Single
from faebryk.libs.picker.picker import does_not_require_picker_check
from faebryk.libs.sets.quantity_sets import Quantity_Interval, Quantity_Set
from faebryk.libs.sets.sets import BoolSet
from faebryk.libs.units import (
    HasUnit,
    P,
    Quantity,
    UnitCompatibilityError,
    dimensionless,
)
from faebryk.libs.units import (
    Unit as UnitType,
)
from faebryk.libs.util import (
    FuncDict,
    cast_assert,
    complete_type_string,
    groupby,
    has_attr_or_property,
    has_instance_settable_attr,
    import_from_path,
    is_type_pair,
    not_none,
    once,
    partition_as_list,
)

logger = logging.getLogger(__name__)


Numeric = Parameter | Arithmetic | Quantity_Set


@dataclass
class Position:
    file: str
    line: int
    col: int


@dataclass
class Span:
    start: Position
    end: Position

    @classmethod
    def from_ctx(cls, ctx: ParserRuleContext) -> "Span":
        file, start_line, start_col, end_line, end_col = get_src_info_from_ctx(ctx)
        return cls(
            Position(str(file), start_line, start_col),
            Position(str(file), end_line, end_col),
        )

    @classmethod
    def from_ctxs(cls, ctxs: Iterable[ParserRuleContext]) -> "Span":
        start_ctx = next(filter(lambda x: x is not None, ctxs))
        end_ctx = last(filter(lambda x: x is not None, ctxs))
        file, start_line, start_col, _, _ = get_src_info_from_ctx(start_ctx)
        _, _, _, end_line, end_col = get_src_info_from_ctx(end_ctx)
        return cls(
            Position(str(file), start_line, start_col),
            Position(str(file), end_line, end_col),
        )

    def contains(self, pos: Position) -> bool:
        return (
            (self.start.file == pos.file)
            and self.start.line <= pos.line
            and self.end.line >= pos.line
            and self.start.col <= pos.col
            and self.end.col >= pos.col
        )


class from_dsl(Trait.decless()):
    def __init__(
        self,
        src_ctx: ParserRuleContext,
        definition_ctx: ap.BlockdefContext | type[L.Node] | None = None,
    ) -> None:
        super().__init__()
        self.src_ctx = src_ctx
        self.definition_ctx = definition_ctx
        self.references: list[Span] = []

        # just a failsafe
        if str(self.src_file.parent).startswith("file:"):
            raise ValueError(f"src_file: {self.src_file}")

    def add_reference(self, ctx: ParserRuleContext) -> None:
        self.references.append(Span.from_ctx(ctx))

    def add_composite_reference(self, *ctxs: ParserRuleContext) -> None:
        self.references.append(Span.from_ctxs(ctxs))

    def set_definition(self, ctx: ap.BlockdefContext | type[L.Node]) -> None:
        self.definition_ctx = ctx

    def query_references(self, file_path: str, line: int, col: int) -> Span | None:
        # TODO: faster
        for ref in self.references:
            if ref.contains(Position(file_path, line, col)):
                return ref
        return None

    def query_definition(
        self, file_path: str, line: int, col: int
    ) -> tuple[Span, Span, Span] | None:
        if self.definition_ctx is None:
            return None

        origin_span = Span.from_ctx(self.src_ctx)
        if origin_span.contains(Position(file_path, line, col)):
            if isinstance(self.definition_ctx, ap.BlockdefContext):
                target_span = Span.from_ctx(self.definition_ctx)
                target_selection_span = Span.from_ctx(self.definition_ctx.name())
            else:
                target_path = inspect.getfile(self.definition_ctx)
                target_lines = inspect.getsourcelines(self.definition_ctx)

                target_start_line = target_lines[1]
                target_end_line = target_start_line + len(target_lines[0]) - 1

                target_span = Span(
                    Position(target_path, target_start_line, 0),
                    Position(target_path, target_end_line, 0),
                )
                target_selection_span = target_span

            return origin_span, target_span, target_selection_span

        return None

    @property
    def hover_text(self) -> str:
        out = f"(node) {self.obj.get_full_name(types=True)}"

        if (
            self.definition_ctx is not None
            and not isinstance(self.definition_ctx, ap.BlockdefContext)
            and (doc := inspect.getdoc(self.definition_ctx)) is not None
        ):
            out += f"\n\n{doc}"

        return out

    @property
    @once
    def src_file(self) -> Path:
        file, _, _, _, _ = get_src_info_from_ctx(self.src_ctx)
        return Path(file)

    @property
    @once
    def definition_file(self) -> Path | None:
        match self.definition_ctx:
            case ap.BlockdefContext():
                file, _, _, _, _ = get_src_info_from_ctx(self.definition_ctx)
                return Path(file)
            case L.Node:
                return Path(inspect.getfile(self.definition_ctx))
            case _:
                return None

    def _describe(self) -> str:
        def _ctx_or_type_to_str(ctx: ParserRuleContext | type[L.Node]) -> str:
            if isinstance(ctx, ParserRuleContext):
                file, start_line, start_col, end_line, end_col = get_src_info_from_ctx(
                    ctx
                )
                return f"{file}:{start_line}:{start_col} - {end_line}:{end_col}"
            elif ctx is not None:
                return f"{inspect.getfile(ctx)}:{inspect.getsourcelines(ctx)[1]}:0"

        return json.dumps(
            {
                "hover_text": self.hover_text,
                "source": _ctx_or_type_to_str(self.src_ctx),
                "definition": _ctx_or_type_to_str(self.definition_ctx)
                if self.definition_ctx is not None
                else None,
                "references": [
                    (
                        f"{ref.start.file}:{ref.start.line}:{ref.start.col} - "
                        f"{ref.end.line}:{ref.end.col}"
                    )
                    for ref in self.references
                ],
            },
            indent=2,
        )


class type_from_dsl(from_dsl):
    def __init__(
        self,
        src_ctx: ParserRuleContext,
        name: str,
        category: Literal["module", "module interface", "trait", "unknown"],
        definition_ctx: ap.BlockdefContext | type[L.Node] | None = None,
    ) -> None:
        super().__init__(src_ctx, definition_ctx)
        self.name = name
        self.category = category

    @property
    def hover_text(self) -> str:
        return f"({self.category}) {self.name}"


@dataclass
class Number:
    value: str
    negative: bool
    base: int

    def interpret(self) -> int | float:
        if self.base != 10:
            out = int(self.value, self.base)
        else:
            out = float(self.value)

        if self.negative:
            out *= -1

        if out.is_integer():
            out = int(out)

        return out


class BasicsMixin:
    def visitName(self, ctx: ap.NameContext) -> str:
        """
        If this is an int, convert it to one (for pins),
        else return the name as a string.
        """
        return ctx.getText()

    def visitTypeReference(self, ctx: ap.Type_referenceContext) -> TypeRef:
        return TypeRef(self.visitName(name) for name in ctx.name())

    def visitArrayIndex(self, ctx: ap.Array_indexContext | None) -> str | int | None:
        if ctx is None:
            return None
        if key := ctx.key():
            out = key.getText()
            if is_int(out):
                return int(out)
            return out
        return None

    def visitFieldReferencePart(
        self, ctx: ap.Field_reference_partContext
    ) -> ReferencePartType:
        return ReferencePartType(
            self.visitName(ctx.name()), self.visitArrayIndex(ctx.array_index())
        )

    def visitFieldReference(self, ctx: ap.Field_referenceContext) -> FieldRef:
        pin = ctx.pin_reference_end()
        if pin is not None:
            pin = self.visitNumber_hint_natural(pin.number_hint_natural())
        return FieldRef(
            parts=(
                self.visitFieldReferencePart(part)
                for part in ctx.field_reference_part()
            ),
            pin=pin,
        )

    def visitString(self, ctx: ap.StringContext) -> str:
        raw: str = ctx.getText()
        return raw.strip("\"'")

    def visitBoolean_(self, ctx: ap.Boolean_Context) -> bool:
        raw: str = ctx.getText()

        if raw.lower() == "true":
            return True
        elif raw.lower() == "false":
            return False

        raise errors.UserException.from_ctx(ctx, f"Expected a boolean value, got {raw}")

    def visitNumber_signless(self, ctx: ap.Number_signlessContext) -> Number:
        number: str = ctx.getText()
        base = 10
        if number.startswith("0") and len(number) > 1:
            if number[1] in "xX":
                base = 16
            elif number[1] in "oO":
                base = 8
            elif number[1] in "bB":
                base = 2
        return Number(number, False, base)

    def visitNumber(self, ctx: ap.NumberContext) -> Number:
        number: Number = self.visitNumber_signless(ctx.number_signless())
        sign = ctx.MINUS()
        negative = bool(sign)
        return Number(number.value, negative, number.base)

    def visitNumber_hint_natural(self, ctx: ap.Number_hint_naturalContext) -> int:
        number = self.visitNumber_signless(ctx.number_signless())
        if number.negative:
            raise errors.UserException.from_ctx(
                ctx, "Natural numbers must be non-negative"
            )

        try:
            return int(number.value, number.base)
        except ValueError as ex:
            raise errors.UserException.from_ctx(
                ctx, "Natural numbers must be whole numbers"
            ) from ex

    def visitNumber_hint_integer(self, ctx: ap.Number_hint_integerContext) -> int:
        number = self.visitNumber(ctx.number())

        try:
            out = int(number.value, number.base)
            if number.negative:
                out = -out
            return out
        except ValueError as ex:
            raise errors.UserException.from_ctx(
                ctx, "Integer numbers must be whole numbers"
            ) from ex


class NOTHING:
    """A sentinel object to represent a "nothing" return value."""


class SkipPriorFailedException(Exception):
    """Raised to skip a statement in case a dependency already failed"""


class DeprecatedException(errors.UserException):
    """
    Raised when a deprecated feature is used.
    """

    def get_frozen(self) -> tuple:
        # TODO: this is a bit of a hack to make the logger de-dup these for us
        return errors._BaseBaseUserException.get_frozen(self)


class SequenceMixin:
    """
    The base translator is responsible for methods common to
    navigating from the top of the AST including how to process
    errors, and commonising return types.
    """

    def defaultResult(self):
        """
        Override the default "None" return type
        (for things that return nothing) with the Sentinel NOTHING
        """
        return NOTHING

    def visit_iterable_helper(self, children: Iterable) -> KeyOptMap:
        """
        Visit multiple children and return a tuple of their results,
        discard any results that are NOTHING and flattening the children's results.
        It is assumed the children are returning their own OptionallyNamedItems.
        """

        def _visit():
            for err_cltr, child in iter_through_errors(
                children,
                errors._BaseBaseUserException,
                SkipPriorFailedException,
            ):
                with err_cltr():
                    # Since we're in a SequenceMixin, we need to cast self to the visitor type # noqa: E501  # pre-existing
                    child_result = cast(AtoParserVisitor, self).visit(child)
                    if child_result is not NOTHING:
                        yield child_result

        child_results = chain.from_iterable(_visit())
        child_results = filter(lambda x: x is not NOTHING, child_results)
        child_results = KeyOptMap(KeyOptItem(cr) for cr in child_results)

        return KeyOptMap(child_results)

    def visitFile_input(self, ctx: ap.File_inputContext) -> KeyOptMap:
        return self.visit_iterable_helper(ctx.stmt())

    def visitSimple_stmts(self, ctx: ap.Simple_stmtsContext) -> KeyOptMap:
        return self.visit_iterable_helper(ctx.simple_stmt())

    def visitBlock(self, ctx: ap.BlockContext) -> KeyOptMap:
        if ctx.stmt():
            return self.visit_iterable_helper(ctx.stmt())
        if ctx.simple_stmts():
            return self.visitSimple_stmts(ctx.simple_stmts())

        raise ValueError  # this should be protected because it shouldn't be parseable


class BlockNotFoundError(errors.UserKeyError):
    """
    Raised when a block doesn't exist.
    """


@dataclass
class Context:
    """~A metaclass to hold context/origin information on ato classes."""

    @dataclass
    class ImportPlaceholder:
        ref: TypeRef
        from_path: str
        original_ctx: ParserRuleContext

    # Location information re. the source of this module
    file_path: Path | None

    # Scope information
    scope_ctx: ap.BlockdefContext | ap.File_inputContext
    refs: dict[TypeRef, Type[L.Node] | ap.BlockdefContext | ImportPlaceholder]
    ref_ctxs: dict[TypeRef, ParserRuleContext]


ImportKeyOptMap = KeyOptMap[
    tuple[Context.ImportPlaceholder, ap.Import_stmtContext, ap.Type_referenceContext]
]


class Wendy(BasicsMixin, SequenceMixin, AtoParserVisitor):  # type: ignore  # Overriding base class makes sense here
    """
    Wendy is Bob's business partner and fellow builder in the children's TV series
    "Bob the Builder." She is a skilled construction worker who often manages the
    business side of their building company while also participating in hands-on
    construction work. Wendy is portrayed as capable, practical and level-headed,
    often helping to keep projects organized and on track. She wears a green safety
    helmet and work clothes, and is known for her competence in operating various
    construction vehicles and equipment.

    Wendy also knows where to find the best building supplies.
    """

    def visitImport_stmt(self, ctx: ap.Import_stmtContext) -> ImportKeyOptMap:
        if from_path := ctx.string():
            lazy_imports = [
                Context.ImportPlaceholder(
                    ref=self.visitTypeReference(reference),
                    from_path=self.visitString(from_path),
                    original_ctx=ctx,
                )
                for reference in ctx.type_reference()
            ]
            return KeyOptMap(
                KeyOptItem.from_kv(li.ref, (li, ctx, reference))
                for reference in ctx.type_reference()
                for li in lazy_imports
            )

        else:
            # Standard library imports are special, and don't require a from path
            imports = []
            for collector, reference in iter_through_errors(ctx.type_reference()):
                with collector():
                    ref = self.visitTypeReference(reference)
                    if len(ref) > 1:
                        raise errors.UserKeyError.from_ctx(
                            ctx, "Standard library imports must be single-name"
                        )

                    name = ref[0]
                    if not hasattr(F, name) or not issubclass(
                        getattr(F, name), (L.Module, L.ModuleInterface, L.Trait)
                    ):
                        raise errors.UserKeyError.from_ctx(
                            reference,
                            f"Unknown standard library module: '{name}'",
                        )

                    imports.append(
                        KeyOptItem.from_kv(ref, (getattr(F, name), ctx, reference))
                    )

            return KeyOptMap(imports)

    def visitDep_import_stmt(self, ctx: ap.Dep_import_stmtContext) -> ImportKeyOptMap:
        lazy_import = Context.ImportPlaceholder(
            ref=self.visitTypeReference(ctx.type_reference()),
            from_path=self.visitString(ctx.string()),
            original_ctx=ctx,
        )
        # TODO: @v0.4 remove this deprecated import form
        with downgrade(DeprecatedException):
            raise DeprecatedException.from_ctx(
                ctx,
                "`import <something> from <path>` is deprecated and"
                " will be removed in a future version. Use "
                f"`from {ctx.string().getText()} import"
                f" {ctx.type_reference().getText()}`"
                " instead.",
            )
        return KeyOptMap.from_kv(
            lazy_import.ref, (lazy_import, ctx, ctx.type_reference())
        )

    def visitBlockdef(self, ctx: ap.BlockdefContext) -> ImportKeyOptMap:
        ref = TypeRef.from_one(self.visitName(ctx.name()))
        return KeyOptMap.from_kv(ref, (ctx, ctx, ctx.name()))

    def visitSimple_stmt(
        self, ctx: ap.Simple_stmtContext | Any
    ) -> ImportKeyOptMap | type[NOTHING]:
        if ctx.import_stmt() or ctx.dep_import_stmt():
            return super().visitChildren(ctx)
        return NOTHING

    # TODO: @v0.4: remove this shimming
    @staticmethod
    def _find_shim(
        file_path: Path | None, ref: TypeRef
    ) -> tuple[Type[L.Node], str] | None:
        if file_path is None:
            return None

        import_addr = address.AddrStr.from_parts(file_path, str(TypeRef(ref)))

        for shim_addr in shim_map:
            if import_addr.endswith(shim_addr):
                return shim_map[shim_addr]

        return None

    @classmethod
    def survey(
        cls, file_path: Path | None, ctx: ap.BlockdefContext | ap.File_inputContext
    ) -> Context:
        surveyor = cls()
        context = Context(file_path=file_path, scope_ctx=ctx, refs={}, ref_ctxs={})
        for ref, (item, item_ctx, item_ref_ctx) in surveyor.visit(ctx):
            assert isinstance(item_ctx, ParserRuleContext)
            if ref in context.refs:
                # Downgrade the error in case we're shadowing things
                # Not limiting the number of times we show this warning
                # because they're pretty important and Wendy is well cached
                with downgrade(errors.UserKeyError):
                    raise errors.UserKeyError.from_ctx(
                        item_ref_ctx,
                        f"`{ref}` already declared. Shadowing original."
                        " In the future this may be an error",
                    )

            # TODO: @v0.4: remove this shimming
            if shim := cls._find_shim(context.file_path, ref):
                shim_cls, preferred = shim

                if hasattr(item_ctx, "name"):
                    dep_ctx = item_ctx.name()  # type: ignore
                elif hasattr(item_ctx, "reference"):
                    dep_ctx = item_ctx.reference()  # type: ignore
                else:
                    dep_ctx = item_ctx

                # TODO: @v0.4 increase the level of this to WARNING
                # when there's an alternative
                with downgrade(DeprecatedException, to_level=logging.DEBUG):
                    raise DeprecatedException.from_ctx(
                        dep_ctx,
                        f"`{ref}` is deprecated and will be removed in a future"
                        f" version. Use `{preferred}` instead.",
                    )

                context.refs[ref] = shim_cls
            else:
                context.refs[ref] = item

            context.ref_ctxs[ref] = item_ref_ctx

        return context

    def visitPragma_stmt(self, ctx: ap.Pragma_stmtContext):
        # pragma experiment() handled in Bob::_is_feature_enabled()
        # test parsing
        try:
            pragma = _parse_pragma(ctx.PRAGMA().getText().strip())[1]
            _FeatureFlags.feature_from_experiment_call(pragma)
        except _FeatureFlags.ExperimentPragmaSyntaxError as ex:
            raise errors.UserSyntaxError.from_ctx(ctx, str(ex)) from ex
        except _FeatureFlags.UnrecognizedExperimentError as ex:
            raise errors.UserFeatureNotAvailableError.from_ctx(ctx, str(ex)) from ex
        except errors.UserException as ex:
            # Re-raise the exception with the context from the pragma statement
            raise errors.UserException.from_ctx(ctx, str(ex)) from ex
        return NOTHING


@contextmanager
def ato_error_converter():
    try:
        yield
    except NodeException as ex:
        if from_dsl_ := ex.node.try_get_trait(from_dsl):
            raise errors.UserException.from_ctx(from_dsl_.src_ctx, str(ex)) from ex
        else:
            raise ex


@contextmanager
def _attach_ctx_to_ex(ctx: ParserRuleContext, traceback: Sequence[ParserRuleContext]):
    try:
        yield
    except errors.UserException as ex:
        if ex.origin_start is None:
            ex.attach_origin_from_ctx(ctx)
            # only attach traceback if we're also setting the origin
            if ex.traceback is None:
                ex.traceback = traceback
        raise ex


_declaration_domain_to_unit = {
    "dimensionless": dimensionless,
    "resistance": P.ohm,
    "capacitance": P.farad,
    "inductance": P.henry,
    "voltage": P.volt,
    "current": P.ampere,
    "power": P.watt,
    "frequency": P.hertz,
}


@dataclass
class _ParameterDefinition:
    """
    Holds information about a parameter declaration or assignment.
    We collect those per parameter in the `Bob._param_assignments` dict.
    Multiple assignments are allowed, but they interact with each other in non-trivial
    ways. Thus we need to track them and process them in the end in
    `_merge_parameter_assignments`.
    """

    ctx: ParserRuleContext
    traceback: Sequence[ParserRuleContext]
    ref: FieldRef
    value: Range | Single | None = None

    @property
    def is_declaration(self) -> bool:
        return self.value is None

    @property
    def is_definition(self) -> bool:
        return not self.is_declaration

    def __post_init__(self):
        pass

    @property
    def is_root_assignment(self) -> bool:
        if not self.is_definition:
            return False
        return len(self.ref) == 1


class _EnumUpgradeError(Exception):
    def __init__(self, *enum_types: type[Enum], arg_name: str):
        self.enum_types = enum_types
        self.arg_name = arg_name


def _try_upgrade_str_to_enum(
    callable_: Callable, arg_name: str, arg_value: str
) -> Enum | str:
    """
    Attempts to convert a string argument to a compatible enum value, based on type
    hints.
    """

    try:
        type_hints = typing.get_type_hints(callable_)
    except NameError:
        # occurs when the type is unresolvable, e.g. due to an `if TYPE_CHECKING` guard
        return arg_value

    type_hint = type_hints[arg_name]

    if isinstance(type_hint, type) and issubclass(type_hint, Enum):
        try:
            return type_hint[arg_value]
        except KeyError:
            raise _EnumUpgradeError(type_hint, arg_name=arg_name)

    elif isinstance(type_hint, UnionType) or typing.get_origin(type_hint) is Union:
        type_args = typing.get_args(type_hint)
        enum_args = [
            t for t in type_args if isinstance(t, type) and issubclass(t, Enum)
        ]

        # assume any matching enum works equivalently well
        if enum_args and isinstance(arg_value, str):
            for t in enum_args:
                try:
                    return t[arg_value]
                except KeyError:
                    pass

            if not any(isinstance(t, type) and issubclass(t, str) for t in type_args):
                raise _EnumUpgradeError(*enum_args, arg_name=arg_name)

    return arg_value


def _parse_pragma(pragma_text: str) -> tuple[str, list[str | int | float | bool]]:
    """
    pragma_stmt: '#pragma' function_call
    function_call: NAME '(' argument (',' argument)* ')'
    argument: literal
    literal: STRING | NUMBER | BOOLEAN

    returns (name, [arg1, arg2, ...])
    """
    import re

    _pragma = "#pragma"
    _function_name = r"(?P<function_name>\w+)"
    _string = r'"([^"]*)"'
    _int = r"(\d+)"
    _args_str = r"(?P<args_str>.*?)"

    pragma_syntax = re.compile(rf"^{_pragma}\s+{_function_name}\(\s*{_args_str}\s*\)$")
    _individual_arg_pattern = re.compile(rf"{_string}|{_int}")
    match = pragma_syntax.match(pragma_text)

    if match is None:
        raise errors.UserSyntaxError(f"Malformed pragma: '{pragma_text}'")

    data = match.groupdict()
    name = data["function_name"]
    args_str = data["args_str"]
    found_args = _individual_arg_pattern.findall(args_str)
    arguments = [
        string_arg if string_arg is not None else int(int_arg)
        for string_arg, int_arg in found_args
    ]
    return name, arguments


class _FeatureFlags:
    class ExperimentPragmaSyntaxError(Exception): ...

    class UnrecognizedExperimentError(Exception): ...

    class Feature(StrEnum):
        BRIDGE_CONNECT = "BRIDGE_CONNECT"
        FOR_LOOP = "FOR_LOOP"
        TRAITS = "TRAITS"
        MODULE_TEMPLATING = "MODULE_TEMPLATING"

    def __init__(self):
        self.flags = set[_FeatureFlags.Feature]()

    def enable(self, feature: Feature):
        self.flags.add(feature)

    def disable(self, feature: Feature):
        self.flags.discard(feature)

    @staticmethod
    def feature_from_experiment_call(args: list[str | int | float | bool]) -> Feature:
        if len(args) != 1:
            raise _FeatureFlags.ExperimentPragmaSyntaxError(
                "Experiment pragma takes exactly one argument"
            )

        feature_name = args[0]
        if not isinstance(feature_name, str):
            raise _FeatureFlags.ExperimentPragmaSyntaxError(
                "Experiment pragma takes a single string argument"
            )
        if feature_name not in _FeatureFlags.Feature:
            raise _FeatureFlags.UnrecognizedExperimentError(
                f"Unknown experiment feature: `{feature_name}`"
            )
        return _FeatureFlags.Feature(feature_name)

    @classmethod
    @once
    def from_file_ctx(cls, file_ctx: ap.File_inputContext) -> "_FeatureFlags":
        """Parses pragmas in a file context and returns the set of enabled features."""
        out = cls()

        experiment_calls = [
            pragma
            for stmt_ctx in file_ctx.stmt()
            if (stmt := stmt_ctx.pragma_stmt()) is not None
            and (pragma := _parse_pragma(stmt.PRAGMA().getText().strip()))[0]
            == "experiment"
        ]

        for _, args in experiment_calls:
            out.enable(_FeatureFlags.feature_from_experiment_call(args))

        return out

    def enabled(self, feature: Feature) -> bool:
        return feature in self.flags

    @classmethod
    def enabled_in_ctx(cls, ctx: ParserRuleContext, feature: Feature) -> bool:
        current_ctx = ctx
        while current_ctx is not None and not isinstance(
            current_ctx, ap.File_inputContext
        ):
            current_ctx = current_ctx.parentCtx

        if not isinstance(current_ctx, ap.File_inputContext):
            # This shouldn't happen if ctx is from a parsed file
            logger.warning(f"Could not find file context for feature check '{feature}'")
            return False  # Default to disabled if context is weird

        flags = cls.from_file_ctx(current_ctx)

        return flags.enabled(feature)


type Field = L.Node | list[L.Node] | dict[str, L.Node] | set[L.Node]


class Bob(BasicsMixin, SequenceMixin, AtoParserVisitor):  # type: ignore  # Overriding base class makes sense here
    """
    Bob is a general contractor who runs his own construction company in the town
    of Fixham Harbour (in earlier episodes, he was based in Bobsville). Recognizable
    by his blue jeans, checked shirt, yellow hard hat, and tool belt, Bob is known
    for his positive catchphrase "Can we fix it? Yes, we can!" He's portrayed as a
    friendly, optimistic problem-solver who takes pride in helping his community
    through various building and repair projects. Bob works closely with his team
    of anthropomorphic construction vehicles and his business partner Wendy,
    tackling each construction challenge with enthusiasm and determination. His
    character embodies values of teamwork, perseverance, and taking pride in one's
    work.
    """

    def __init__(self) -> None:
        super().__init__()
        self._scopes = FuncDict[ParserRuleContext, Context]()
        self._python_classes = FuncDict[ap.BlockdefContext, Type[L.Module]]()
        self._node_stack = StackList[L.Node]()
        self._traceback_stack = StackList[ParserRuleContext]()

        self._param_assignments = defaultdict[Parameter, list[_ParameterDefinition]](
            list
        )
        self.search_paths: list[os.PathLike] = []

        # Keeps track of the nodes whose construction failed,
        # so we don't report dud key errors when it was a higher failure
        # that caused the node not to exist
        self._failed_nodes = FuncDict[L.Node, set[str]]()
        self._in_for_loop = False  # Flag to detect nested loops

    def _ensure_feature_enabled(
        self, ctx: ParserRuleContext, feature: _FeatureFlags.Feature
    ) -> None:
        # note syntax errors will be caught before this point

        if not _FeatureFlags.enabled_in_ctx(ctx, feature):
            raise errors.UserFeatureNotEnabledError.from_ctx(
                ctx,
                message=(
                    "Experimental feature not enabled. "
                    f'Use `#pragma experiment("{feature.value}")` in your file.'
                ),
                traceback=self.get_traceback(),
            )

    def build_ast(
        self, ast: ap.File_inputContext, ref: TypeRef, file_path: Path | None = None
    ) -> L.Node:
        """Build a Module from an AST and reference."""
        file_path = self._sanitise_path(file_path) if file_path else None
        context = self.index_ast(ast, file_path)
        return self._build(context, ref)

    def build_file(self, path: Path, ref: TypeRef) -> L.Node:
        """Build a Module from a file and reference."""
        context = self.index_file(self._sanitise_path(path))
        return self._build(context, ref)

    def build_text(self, text: str, path: Path, ref: TypeRef) -> L.Node:
        """Build a Module from a string and reference."""
        context = self.index_text(text, path)
        return self._build(context, ref)

    def build_node(self, text: str, path: Path, ref: TypeRef) -> L.Node:
        """Build a single node from a string and reference."""
        context = self.index_text(text, path)

        if ref not in context.refs:
            raise errors.UserKeyError.from_ctx(
                context.scope_ctx, f"No declaration of `{ref}` in {context.file_path}"
            )
        try:
            class_ = self._get_referenced_class(context.scope_ctx, ref)

            if isinstance(class_, Context.ImportPlaceholder):
                raise NotImplementedError("ImportPlaceholder")

            with self._init_node(class_) as node:
                node.add(F.is_app_root())
                match node:
                    case L.Module():
                        category = "module"
                    case L.Trait():
                        category = "trait"
                    case L.ModuleInterface():
                        category = "module interface"
                    case _:
                        category = "unknown"
                from_dsl_ = node.add(
                    type_from_dsl(
                        context.ref_ctxs[ref],
                        name=str(ref),
                        category=category,
                        definition_ctx=class_,
                    )
                )
                from_dsl_.add_reference(context.ref_ctxs[ref])

            return node
        except* SkipPriorFailedException as e:
            raise errors.UserException("Build failed") from e

    def _try_build_all(self, context: Context) -> dict[TypeRef, L.Node]:
        out = {}
        with accumulate(errors.UserException) as accumulator:
            for ref in context.refs:
                if isinstance(context.refs[ref], ap.BlockdefContext):
                    with accumulator.collect():
                        out[ref] = self._build(context, ref)

        return out

    def try_build_all_from_file(self, path: Path) -> dict[TypeRef, L.Node]:
        """
        Build each top-level block in a file.

        Returns a dict of successful builds, keyed by reference.
        """
        context = self.index_file(self._sanitise_path(path))
        return self._try_build_all(context)

    def try_build_all_from_text(self, text: str, path: Path) -> dict[TypeRef, L.Node]:
        """
        Build each top-level block in a string.

        Returns a dict of successful builds, keyed by reference.
        """
        context = self.index_text(text, path)
        return self._try_build_all(context)

    @property
    def modules(self) -> dict[address.AddrStr, Type[L.Module]]:
        """Conceptually similar to `sys.modules`"""

        # FIXME: this feels like a shit way to get addresses of the imported modules
        def _get_addr(ctx: ParserRuleContext):
            ref = tuple()
            ctx_ = ctx
            while ctx_ not in self._scopes:
                if isinstance(ctx_, ap.BlockdefContext):
                    ref = (ctx_.name().getText(),) + ref
                ctx_ = ctx_.parentCtx
                if ctx_ is None:
                    return None

            return address.AddrStr.from_parts(
                self._scopes[ctx_].file_path, str(TypeRef(ref))
            )

        return {
            addr: cls
            for ctx, cls in self._python_classes.items()
            if (addr := _get_addr(ctx)) is not None
        }

    def _build(self, context: Context, ref: TypeRef) -> L.Node:
        assert self._is_reset()

        if ref not in context.refs:
            raise errors.UserKeyError.from_ctx(
                context.scope_ctx, f"No declaration of `{ref}` in {context.file_path}"
            )
        try:
            class_ = self._get_referenced_class(context.scope_ctx, ref)
            if not isinstance(class_, ap.BlockdefContext):
                raise errors.UserNotImplementedError(
                    "Can't initialize a fabll directly like this"
                )
            with self._traceback_stack.enter(class_.name()):
                with self._init_node(class_) as node:
                    node.add(F.is_app_root())
                    from_dsl_ = node.add(
                        type_from_dsl(
                            class_,
                            name=class_.name().getText(),
                            category="module",
                        )
                    )
                    from_dsl_.add_reference(class_.name())
                return node
        except* SkipPriorFailedException:
            raise errors.UserException("Build failed")
        finally:
            self._finish()

    def reset(self):
        self._scopes.clear()
        self._python_classes.clear()
        self._node_stack.clear()
        self._traceback_stack.clear()
        self._param_assignments.clear()
        self._failed_nodes.clear()
        self._in_for_loop = False

    def _is_reset(self) -> bool:
        """
        Make sure caches that aren't intended to be shared between builds are empty.
        True if the caches are empty, False if they are not.
        """
        return (
            not self._node_stack
            and not self._traceback_stack
            and not self._param_assignments
        )

    def _finish(self):
        self._merge_parameter_assignments()
        assert self._is_reset()

    class ParamAssignmentIsGospel(errors.UserException):
        """
        The parameter assignment is treated as the precise specification of the
        component, rather than merely as a requirement for it's later selection
        """

        title = "Parameter assignments are component definition"  # type: ignore

    def _merge_parameter_assignments(self):
        with accumulate(
            errors._BaseBaseUserException, SkipPriorFailedException
        ) as ex_acc:
            # Handle missing definitions
            params_without_defitions, params_with_definitions = partition_as_list(
                lambda p: any(a.is_definition for a in self._param_assignments[p]),
                self._param_assignments,
            )

            for param in params_without_defitions:
                last_declaration = last(self._param_assignments.pop(param))
                with ex_acc.collect(), ato_error_converter():
                    # TODO: @v0.4 remove this deprecated import form
                    with downgrade(
                        errors.UserActionWithoutEffectError, to_level=logging.DEBUG
                    ):
                        raise errors.UserActionWithoutEffectError.from_ctx(
                            last_declaration.ctx,
                            f"Attribute `{param}` declared but never assigned.",
                            traceback=last_declaration.traceback,
                        )
            # Handle parameter assignments
            # assignments override each other
            # assignments made in the block definition of the component are "is"
            # external assignments are requirements treated as a subset

            # Allowing external assignments in the first place is a bit weird
            # Got to figure out how people are using this.
            # My guess is that in 99% of cases you can replace them by a `&=`
            params_by_node = groupby(
                params_with_definitions, key=lambda p: p.get_parent_force()[0]
            )
            for assignee_node, assigned_params in params_by_node.items():
                is_part_module = isinstance(assignee_node, L.Module) and (
                    assignee_node.has_trait(F.is_pickable_by_supplier_id)
                    or assignee_node.has_trait(F.is_pickable_by_part_number)
                )

                gospel_params: list[Parameter] = []
                for param in assigned_params:
                    assignments = self._param_assignments.pop(param)
                    definitions = [a for a in assignments if a.is_definition]
                    non_root_definitions, root_definitions = partition_as_list(
                        lambda a: a.is_root_assignment, definitions
                    )

                    assert definitions
                    for definition in definitions:
                        logger.debug(
                            "Assignment:  %s [%s] := %s",
                            param,
                            definition.ref,
                            definition.value,
                        )

                    # Don't see how this could happen, but just in case
                    root_after_external = (False, True) in pairwise(
                        a.is_root_assignment for a in definitions
                    )
                    assert not root_after_external

                    with ex_acc.collect(), ato_error_converter():
                        # Workaround for missing difference between alias and subset
                        # Only relevant for code-as-data part modules
                        # TODO: consider a warning for definitions that aren't purely
                        # narrowing
                        if is_part_module and non_root_definitions:
                            raise errors.UserNotImplementedError.from_ctx(
                                last(non_root_definitions).ctx,
                                "You can't assign to a `component` with a specific"
                                " part number outside of its definition",
                                traceback=last(non_root_definitions).traceback,
                            )

                        elif is_part_module and root_definitions:
                            param.alias_is(not_none(last(root_definitions).value))  # type: ignore
                            param.add(does_not_require_picker_check())
                            gospel_params.append(param)

                        elif not is_part_module:
                            definition = last(definitions)
                            value = not_none(definition.value)
                            try:
                                logger.debug("Constraining %s to %s", param, value)
                                param.constrain_subset(value)  # type: ignore
                            except UnitCompatibilityError as ex:
                                raise errors.UserTypeError.from_ctx(
                                    definition.ctx,
                                    str(ex),
                                    traceback=definition.traceback,
                                ) from ex

                if gospel_params:
                    with downgrade(self.ParamAssignmentIsGospel, to_level=logging.INFO):
                        raise self.ParamAssignmentIsGospel(
                            f"`component` `{assignee_node.get_full_name()}`"
                            " is completely specified by a part number, so these"
                            " params are treated as its exact specification:"
                            + ", ".join(f"`{p}`" for p in gospel_params)
                        )

    @property
    def _current_node(self) -> L.Node:
        return self._node_stack[-1]

    def get_traceback(self) -> Sequence[ParserRuleContext]:
        """Return the current traceback, with sequential duplicates removed"""
        # Use dict ordering guarantees and key uniqueness to remove duplicates
        return list(dict.fromkeys(self._traceback_stack).keys())

    @staticmethod
    def _sanitise_path(path: os.PathLike) -> Path:
        return Path(path).expanduser().resolve().absolute()

    def index_ast(
        self, ast: ap.File_inputContext, file_path: Path | None = None
    ) -> Context:
        if ast in self._scopes:
            return self._scopes[ast]

        context = Wendy.survey(file_path, ast)
        self._scopes[ast] = context
        return context

    def index_file(self, file_path: Path) -> Context:
        ast = parser.get_ast_from_file(file_path)
        return self.index_ast(ast, file_path)

    def index_text(self, text: str, file_path: Path | None) -> Context:
        ast = parser.get_ast_from_text(text, file_path)
        return self.index_ast(ast, file_path)

    def _get_search_paths(self, context: Context) -> list[Path]:
        search_paths = [Path(p) for p in self.search_paths]

        if context.file_path is not None:
            search_paths.insert(0, context.file_path.parent)

        if config.has_project:
            search_paths += [
                config.project.paths.src,
                config.project.paths.modules,
            ]

        # Add the library directory to the search path too
        search_paths.append(Path(inspect.getfile(F)).parent)

        # The root of the project is always a search path
        if (file_path := context.file_path) is not None and (
            pkg_path := find_project_dir(file_path)
        ) is not None:
            search_paths.append(pkg_path)

        return search_paths

    def _find_import_path(self, context: Context, item: Context.ImportPlaceholder):
        # allow importing <src path>/file.suffix as either:
        # from "file.suffix" import X
        # or
        # from "<owner>/<package>/file.suffix" import X

        if (
            pkg_cfg := config.project.package
        ) is not None and item.from_path.startswith(pkg_cfg.identifier):
            item.from_path = item.from_path.replace(
                pkg_cfg.identifier, str(config.project.paths.src), count=1
            )

        # Build up search paths to check for the import in
        # Iterate though them, checking if any contains the thing we're looking for
        search_paths = self._get_search_paths(context)
        for search_path in search_paths:
            candidate_from_path = search_path / item.from_path
            if candidate_from_path.exists():
                break
        else:
            raise errors.UserFileNotFoundError.from_ctx(
                item.original_ctx, f"Unable to resolve import `{item.from_path}`"
            )

        return self._sanitise_path(candidate_from_path)

    def _import_item(
        self, context: Context, item: Context.ImportPlaceholder
    ) -> Type[L.Node] | ap.BlockdefContext:
        from_path = self._find_import_path(context, item)

        if from_path.suffix == ".py":
            try:
                node = import_from_path(from_path)
            except FileNotFoundError as ex:
                raise errors.UserImportNotFoundError.from_ctx(
                    item.original_ctx, str(ex)
                ) from ex

            for ref in item.ref:
                try:
                    node = getattr(node, ref)
                except AttributeError as ex:
                    raise errors.UserKeyError.from_ctx(
                        item.original_ctx,
                        f"Could not find `{ref}` in {node.__file__}",
                        markdown=False,
                    ) from ex

            assert isinstance(node, type) and issubclass(node, L.Node)
            return node

        elif from_path.suffix == ".ato":
            context = self.index_file(from_path)
            if item.ref not in context.refs:
                raise errors.UserKeyError.from_ctx(
                    item.original_ctx, f"No declaration of `{item.ref}` in {from_path}"
                )
            node = context.refs[item.ref]

            if isinstance(node, Context.ImportPlaceholder):
                raise errors.UserTypeError.from_ctx(
                    item.original_ctx,
                    "Importing an import is not supported",
                )

            assert (
                isinstance(node, type)
                and issubclass(node, L.Node)
                or isinstance(node, ap.BlockdefContext | ap.File_inputContext)
            )
            return node

        else:
            raise errors.UserImportNotFoundError.from_ctx(
                item.original_ctx, f"Can't import file type {from_path.suffix}"
            )

    def _get_referenced_class(
        self, ctx: ParserRuleContext, ref: TypeRef
    ) -> Type[L.Node] | ap.BlockdefContext:
        """
        Returns the class / object referenced by the given ref,
        based on Bob's current context. The contextual nature
        of this means that it's only useful during the build process.
        """
        # No change in position from the current context
        # return self, eg the current parser context
        if ref == tuple():
            if isinstance(ctx, ap.BlockdefContext):
                return ctx
            else:
                raise ValueError(f"Can't get class `{ref}` from {ctx}")

        # Ascend the tree until we find a scope that has the ref within it
        ctx_ = ctx
        while ctx_ not in self._scopes:
            if ctx_.parentCtx is None:
                raise ValueError(f"No scope found for `{ref}`")
            ctx_ = ctx_.parentCtx

        context = self._scopes[ctx_]

        # FIXME: there are more cases to check here,
        # eg. if we have part of a ref resolved
        if ref not in context.refs:
            raise errors.UserKeyError.from_ctx(
                ctx, f"No class or block definition found for `{ref}`"
            )

        item = context.refs[ref]
        # Ensure the item is resolved, if not already
        if isinstance(item, Context.ImportPlaceholder):
            # TODO: search path for these imports
            item = self._import_item(context, item)
            context.refs[ref] = item

        return item

    def resolve_node_property(self, node: L.Node, name: str) -> Field:
        if has_attr_or_property(node, name):
            return getattr(node, name)
        if name in node.runtime:
            return node.runtime[name]

        # If we know that a previous failure prevented the creation
        # of this node, raise a SkipPriorFailedException to prevent
        # error messages about it missing from polluting the output
        if name in self._failed_nodes.get(node, set()):
            raise SkipPriorFailedException()

        raise AttributeError(name=name, obj=node)

    def resolve_node_field_part(self, node: L.Node, ref: ReferencePartType) -> Field:
        field = self.resolve_node_property(node, ref.name)

        if isinstance(field, L.Node):
            if ref.key is not None:
                raise ValueError(f"{ref.name} is not subscriptable")
            return field

        if isinstance(field, dict):
            if ref.key is None:
                return field
            if ref.key not in field:
                raise AttributeError(name=f"{ref.name}[{ref.key}]", obj=node)
            return field[ref.key]

        if isinstance(field, list):
            if ref.key is None:
                return field
            if not isinstance(ref.key, int):
                raise ValueError(f"Key `{ref.key}` is not an integer")
            if ref.key >= len(field):
                raise AttributeError(name=f"{ref.name}[{ref.key}]", obj=node)
            return field[ref.key]

        raise TypeError(f"Unknown field type `{type(field)}`")

    def resolve_node_field(self, src_node: L.Node, ref: FieldRef) -> Field:
        path: list[Field] = [src_node]
        for depth, name in enumerate(ref):
            last = path[-1]
            if not isinstance(last, L.Node):
                raise ValueError(
                    f"{name} is a container and can't be dot accessed."
                    f"Did you mean to subscript it like this `{name}[0]`?"
                )
            try:
                field = self.resolve_node_field_part(last, name)
            except AttributeError as ex:
                raise AttributeError(
                    f"`{FieldRef(ref.parts[:depth])}` has no attribute `{ex.name}`"
                    if len(path) > 1
                    else f"No attribute `{name}`"
                ) from ex
            path.append(field)
        return path[-1]

    def resolve_node(
        self, src_node: L.Node, ref: FieldRef | ReferencePartType
    ) -> L.Node:
        if isinstance(ref, ReferencePartType):
            ref = FieldRef([ref])
        field = self.resolve_node_field(src_node, ref)
        if not isinstance(field, L.Node):
            raise TypeError(field, f"{ref} is not a node")
        if isinstance(field, L.Module):
            return field.get_most_special()
        return field

    def resolve_field_shortcut(
        self, src_node: L.Node, name: str, key: KeyType | None = None
    ) -> Field:
        """
        Shortcut for `resolve_field(src_node, FieldRef([ReferencePartType(name, key)]))`
        Useful for tests
        """
        return self.resolve_node_field(
            src_node, FieldRef([ReferencePartType(name, key)])
        )

    def resolve_node_shortcut(
        self, src_node: L.Node, name: str, key: KeyType | None = None
    ) -> L.Node:
        """
        Shortcut for `resolve_node(src_node, FieldRef([ReferencePartType(name, key)]))`
        Useful for tests
        """
        return self.resolve_node(src_node, FieldRef([ReferencePartType(name, key)]))

    def _get_referenced_node(self, ref: FieldRef, ctx: ParserRuleContext) -> L.Node:
        try:
            return self.resolve_node(self._current_node, ref)
        except AttributeError as ex:
            raise errors.UserKeyError.from_ctx(
                ctx, str(ex), traceback=self.get_traceback()
            ) from ex
        except ValueError as ex:
            raise errors.UserKeyError.from_ctx(
                ctx, str(ex), traceback=self.get_traceback()
            ) from ex
        except TypeError as ex:
            raise errors.UserTypeError.from_ctx(
                ctx, str(ex), traceback=self.get_traceback()
            ) from ex

    def _try_get_referenced_node(
        self, ref: FieldRef, ctx: ParserRuleContext
    ) -> L.Node | None:
        try:
            return self._get_referenced_node(ref, ctx)
        except errors.UserKeyError:
            return None

    def _new_node(
        self,
        item: ap.BlockdefContext | Type[L.Node],
        promised_supers: list[ap.BlockdefContext],
        kwargs: dict[str, Any] | None = None,
    ) -> tuple[L.Node, list[ap.BlockdefContext]]:
        """
        Kind of analogous to __new__ in Python, except that it's a factory

        Descends down the class hierarchy until it finds a known base class.
        As it descends, it logs all superclasses it encounters, as `promised_supers`.
        These are accumulated lowest (base-class) to highest (what was initialised).

        Once a base class is found, it creates a new class for each superclass that
        isn't already known, attaching the __atopile_src_ctx__ attribute to the new
        class.
        """
        kwargs = kwargs or {}

        if isinstance(item, type) and issubclass(item, L.Node):
            super_class = item
            for super_ctx in promised_supers:
                if super_ctx in self._python_classes:
                    super_class = self._python_classes[super_ctx]
                    continue

                assert issubclass(super_class, L.Node)

                # Create a new type with a more descriptive name
                type_name = super_ctx.name().getText()
                type_qualname = f"{super_class.__module__}.{type_name}"

                super_class = type(
                    type_name,  # Class name
                    (super_class,),  # Base classes
                    {
                        "__module__": super_class.__module__,
                        "__qualname__": type_qualname,
                        "__atopile_src_ctx__": super_ctx,
                    },
                )

                self._python_classes[super_ctx] = super_class

            assert issubclass(super_class, L.Node)

            callable_ = getattr(super_class, "__original_init__")
            super_class_signature = inspect.signature(callable_)

            for arg_name, arg_value in kwargs.items():
                if arg_name not in super_class_signature.parameters:
                    raise errors.UserBadParameterError(
                        f"Unknown argument `{arg_name}` for `{super_class}`"
                    )

                if isinstance(arg_value, str):
                    try:
                        kwargs[arg_name] = _try_upgrade_str_to_enum(
                            callable_, arg_name, arg_value
                        )
                    except _EnumUpgradeError as ex:
                        raise errors.UserInvalidValueError.from_ctx(
                            origin=None,  # TODO: add context
                            enum_types=ex.enum_types,
                            enum_name=arg_name,
                            value=arg_value,
                        ) from ex

            return super_class(**kwargs), promised_supers

        if isinstance(item, ap.BlockdefContext):
            # Find the superclass of the new node, if there's one defined
            block_type = item.blocktype()
            if super_ctx := item.blockdef_super():
                super_ref = self.visitTypeReference(super_ctx.type_reference())
                # Create a base node to build off
                base_class = self._get_referenced_class(item, super_ref)
            else:
                # Create a shell of base-node to build off
                assert isinstance(block_type, ap.BlocktypeContext)
                if block_type.INTERFACE():
                    base_class = L.ModuleInterface
                elif block_type.COMPONENT():
                    base_class = L.Module
                elif block_type.MODULE():
                    base_class = L.Module
                else:
                    raise ValueError(f"Unknown block type `{block_type.getText()}`")

            # Descend into building the superclass. We've got no information
            # on when the super-chain will be resolved, so we need to promise
            # that this current blockdef will be visited as part of the init
            result = self._new_node(
                base_class,
                promised_supers=[item] + promised_supers,
            )

            return result

        # This should never happen
        raise ValueError(f"Unknown item type `{item}`")

    @contextmanager
    def _init_node(
        self,
        node_type: ap.BlockdefContext | Type[L.Node],
        kwargs: dict[str, Any] | None = None,
    ) -> Generator[L.Node, None, None]:
        """
        Kind of analogous to __init__ in Python, except that it's a factory

        Pre-yield it is analogous to __new__, where it creates the hollow instance
        Post-yield it is analogous to __init__, where it fills in the details

        This is to allow for it to be attached in the graph before it's filled,
        and subsequently for errors to be raised in context of it's graph location.
        """
        new_node, promised_supers = self._new_node(
            node_type, promised_supers=[], kwargs=kwargs
        )

        # Shim on component and module classes defined in ato
        # Do not shim fabll modules, or interfaces
        if isinstance(node_type, ap.BlockdefContext):
            if node_type.blocktype().COMPONENT() or node_type.blocktype().MODULE():
                # Some shims add the trait themselves
                if not new_node.has_trait(_has_ato_cmp_attrs):
                    new_node.add(_has_ato_cmp_attrs())

            if not new_node.has_trait(from_dsl):
                from_dsl_ = new_node.add(from_dsl(node_type))
                from_dsl_.set_definition(node_type)

        yield new_node
        with self._node_stack.enter(new_node):
            for super_ctx in promised_supers:
                # TODO: this would be better if we had the
                # "from xyz" super in the traceback too
                with self._traceback_stack.enter(super_ctx.name()):
                    self.visitBlock(super_ctx.block())

        # Deferred to after node is fully initialised
        traits = new_node.get_children(direct_only=True, types=L.Trait)
        for trait in traits:
            if trait.has_trait(F.is_lazy):
                assert TraitImpl.is_traitimpl(trait)
                cast(TraitImpl, trait).on_obj_set()

    def _get_param(
        self, node: L.Node, ref: ReferencePartType, src_ctx: ParserRuleContext
    ) -> Parameter:
        """
        Get a param from a node.
        Not supported: If it doesn't exist, create it and promise to assign
        it later. Used in forward-declaration.
        """
        try:
            node = self.resolve_node(node, ref)
        except AttributeError as ex:
            # Wah wah wah - we don't know what this is
            raise errors.UserNotImplementedError.from_ctx(
                src_ctx,
                f"Parameter `{ref}` not found and"
                " forward-declared params are not yet implemented",
                traceback=self.get_traceback(),
            ) from ex
        except ValueError as ex:
            raise errors.UserValueError.from_ctx(
                src_ctx, str(ex), traceback=self.get_traceback()
            ) from ex

        if not isinstance(node, Parameter):
            raise errors.UserSyntaxError.from_ctx(
                src_ctx,
                f"Node {ref} is {type(node)} not a Parameter",
                traceback=self.get_traceback(),
            )
        return node

    def _ensure_param(
        self,
        node: L.Node,
        ref: ReferencePartType,
        unit: UnitType,
        src_ctx: ParserRuleContext,
    ) -> Parameter:
        """
        Ensure a node has a param with a given name
        If it already exists, check the unit is compatible and return it
        """

        try:
            param = self.resolve_node(node, ref)
        except AttributeError:
            # Here we attach only minimal information, so we can override it later
            if ref.key is not None:
                if not isinstance(ref.key, str):
                    raise errors.UserNotImplementedError.from_ctx(
                        src_ctx,
                        f"Can't forward assign to a non-string key `{ref}`",
                        traceback=self.get_traceback(),
                    )
                container = getattr(node, ref.name)
                param = node.add(
                    Parameter(units=unit, domain=L.Domains.Numbers.REAL()),
                    name=ref.key,
                    container=container,
                )
            else:
                param = node.add(
                    Parameter(units=unit, domain=L.Domains.Numbers.REAL()),
                    name=ref.name,
                )
        except ValueError as ex:
            raise errors.UserValueError.from_ctx(
                src_ctx, str(ex), traceback=self.get_traceback()
            ) from ex
        else:
            if not isinstance(param, Parameter):
                raise errors.UserTypeError.from_ctx(
                    src_ctx,
                    f"Cannot assign a parameter to `{ref}` on `{node}` because its"
                    f" type is `{param.__class__.__name__}`",
                    traceback=self.get_traceback(),
                )

        if not param.units.is_compatible_with(unit):
            raise errors.UserIncompatibleUnitError.from_ctx(
                src_ctx,
                f"Given units ({unit}) are incompatible"
                f" with existing units ({param.units}).",
                traceback=self.get_traceback(),
            )

        return param

    def _record_failed_node(self, node: L.Node, name: str):
        self._failed_nodes.setdefault(node, set()).add(name)

    def _assign_new_node(
        self,
        ctx: ap.Assign_stmtContext,
        assignable_ctx: ap.AssignableContext,
        assigned_ctx: ap.Field_referenceContext,
        assigned_ref: FieldRef,
    ):
        if len(assigned_ref) > 1:
            raise errors.UserSyntaxError.from_ctx(
                ctx,
                f"Can't declare fields in a nested object `{assigned_ref}`",
                traceback=self.get_traceback(),
            )

        assigned_name = assigned_ref[-1]
        if assigned_name.key is not None:
            raise errors.UserSyntaxError.from_ctx(
                ctx,
                f"Can't use keys with `new` statements `{assigned_ref}`",
                traceback=self.get_traceback(),
            )
        new_stmt_ctx = assignable_ctx.new_stmt()
        type_ref_ctx = new_stmt_ctx.type_reference()
        ref = self.visitTypeReference(type_ref_ctx)

        if new_stmt_ctx.template() is not None:
            self._ensure_feature_enabled(
                new_stmt_ctx, _FeatureFlags.Feature.MODULE_TEMPLATING
            )

        kwargs = self.visitTemplate(new_stmt_ctx.template())

        def _add_node(
            obj: L.Node,
            node: L.Node,
            container_name: str | None = None,
            node_type: type[L.Node] | ap.BlockdefContext | None = None,
        ):
            try:
                obj.add(
                    node,
                    name=assigned_name.name if container_name is None else None,
                    container=getattr(obj, container_name) if container_name else None,
                )
            except FieldExistsError as e:
                raise errors.UserAlreadyExistsError.from_ctx(
                    ctx,
                    f"Field `{assigned_name}` already exists",
                    traceback=self.get_traceback(),
                ) from e

            from_dsl_ = node.add(from_dsl(type_ref_ctx))
            from_dsl_.add_reference(assigned_ctx)

            if node_type is not None and isinstance(node_type, ap.BlockdefContext):
                from_dsl_.set_definition(node_type)

        try:
            with self._traceback_stack.enter(new_stmt_ctx):
                if new_count_ctx := new_stmt_ctx.new_count():
                    try:
                        new_count = int(new_count_ctx.getText())
                    except ValueError:
                        raise errors.UserValueError.from_ctx(
                            ctx,
                            f"Invalid integer `{new_count_ctx.getText()}`",
                            traceback=self.get_traceback(),
                        )

                    if new_count < 0:
                        raise errors.UserValueError.from_ctx(
                            ctx,
                            f"Negative integer `{new_count}`",
                            traceback=self.get_traceback(),
                        )

                    if hasattr(self._current_node, assigned_name.name):
                        raise errors.UserAlreadyExistsError.from_ctx(
                            ctx,
                            f"Field `{assigned_name}` already exists",
                            traceback=self.get_traceback(),
                        )

                    setattr(self._current_node, assigned_name.name, list())
                    for _ in range(new_count):
                        node_type = self._get_referenced_class(ctx, ref)
                        with self._init_node(node_type, kwargs=kwargs) as new_node:
                            _add_node(
                                self._current_node,
                                node=new_node,
                                container_name=assigned_name.name,
                                node_type=node_type,
                            )
                else:
                    node_type = self._get_referenced_class(
                        new_stmt_ctx.type_reference(), ref
                    )
                    with self._init_node(node_type, kwargs=kwargs) as new_node:
                        _add_node(
                            self._current_node, node=new_node, node_type=node_type
                        )
        except Exception:
            # Not a narrower exception because it's often an ExceptionGroup
            self._record_failed_node(self._current_node, assigned_name.name)
            raise

    def _assign_arithmetic(
        self,
        ctx: ap.Assign_stmtContext,
        assigned_ref: FieldRef,
        target: L.Node,
    ):
        if declaration := ctx.field_reference_or_declaration().declaration_stmt():
            # check valid declaration
            # create param with corresponding units
            self.visitDeclaration_stmt(declaration)

        assignable_ctx = ctx.assignable()
        assigned_name = assigned_ref[-1]
        value = self.visit(assignable_ctx)
        unit = HasUnit.get_units(value)
        param = self._ensure_param(target, assigned_name, unit, ctx)

        self._param_assignments[param].append(
            _ParameterDefinition(
                ref=assigned_ref,
                value=value,
                ctx=ctx,
                traceback=self.get_traceback(),
            )
        )

    def _assign_string_or_bool(
        self,
        ctx: ap.Assign_stmtContext,
        assignable_ctx: ap.AssignableContext,
        assigned_ref: FieldRef,
        target: L.Node,
    ):
        assigned_name = assigned_ref[-1]

        if assigned_name.key is not None:
            raise errors.UserSyntaxError.from_ctx(
                ctx,
                f"Can't use keys with non-arithmetic attribute assignments "
                f"`{assigned_ref}`",
                traceback=self.get_traceback(),
            )

        value = self.visit(assignable_ctx)

        # Check if it's a property or attribute that can be set
        if has_instance_settable_attr(target, assigned_name.name):
            try:
                attr = getattr(target, assigned_name.name)
            except AttributeError:
                attr = None

            if (
                attr is not None
                and isinstance(attr, Parameter)
                # non-string enum values would need parser changes
                and isinstance(value, str)
                and isinstance(attr.domain, L.Domains.ENUM)
            ):
                try:
                    value = attr.domain.enum_t[value]
                except KeyError:
                    raise errors.UserInvalidValueError.from_ctx(
                        origin=assignable_ctx,
                        enum_types=(attr.domain.enum_t,),
                        enum_name=assigned_name.name,
                        value=value,
                        traceback=self.get_traceback(),
                    )

                attr.constrain_subset(value)

            else:
                try:
                    setattr(target, assigned_name.name, value)
                except errors.UserException as e:
                    e.attach_origin_from_ctx(assignable_ctx)
                    raise
        elif (
            # If ModuleShims has a settable property, use it
            hasattr(GlobalAttributes, assigned_name.name)
            and isinstance(getattr(GlobalAttributes, assigned_name.name), property)
            and getattr(GlobalAttributes, assigned_name.name).fset
        ):
            prop = cast_assert(property, getattr(GlobalAttributes, assigned_name.name))
            assert prop.fset is not None
            # TODO: @v0.4 remove this deprecated import form
            with (
                downgrade(DeprecatedException, errors.UserNotImplementedError),
                _attach_ctx_to_ex(assignable_ctx, self.get_traceback()),
            ):
                prop.fset(target, value)
        else:
            # Strictly, these are two classes of errors that could use independent
            # suppression, but we'll just suppress them both collectively for now
            # TODO: @v0.4 remove this deprecated import form
            with downgrade(errors.UserException):
                raise errors.UserException.from_ctx(
                    ctx,
                    f"Ignoring assignment of `{value}` to `{assigned_name}` on"
                    f" `{target}`",
                    traceback=self.get_traceback(),
                )

    def visitAssign_stmt(self, ctx: ap.Assign_stmtContext):
        """Assign values and create new instances of things."""
        assignable_ctx = ctx.assignable()
        dec = ctx.field_reference_or_declaration()
        assigned_ref = self.visitFieldReference(
            dec.field_reference() or dec.declaration_stmt().field_reference()
        )
        target = self._get_referenced_node(assigned_ref.stem, ctx)

        if assignable_ctx.new_stmt():
            self._assign_new_node(
                ctx=ctx,
                assignable_ctx=assignable_ctx,
                assigned_ctx=dec,
                assigned_ref=assigned_ref,
            )
        elif (
            assignable_ctx.literal_physical() or assignable_ctx.arithmetic_expression()
        ):
            self._assign_arithmetic(ctx=ctx, assigned_ref=assigned_ref, target=target)
        elif assignable_ctx.string() or assignable_ctx.boolean_():
            self._assign_string_or_bool(
                ctx=ctx,
                assignable_ctx=assignable_ctx,
                assigned_ref=assigned_ref,
                target=target,
            )
        else:
            raise ValueError(f"Unhandled assignable type `{assignable_ctx.getText()}`")

        return NOTHING

    def _get_mif_and_warn_when_exists(
        self, name: ReferencePartType, ctx: ParserRuleContext
    ) -> L.ModuleInterface | None:
        try:
            mif = self.resolve_node(self._current_node, name)
        except AttributeError:
            return None
        except ValueError as ex:
            raise errors.UserValueError.from_ctx(
                ctx, str(ex), traceback=self.get_traceback()
            ) from ex

        if isinstance(mif, L.ModuleInterface):
            # TODO: @v0.4 remove this deprecated import form
            with downgrade(errors.UserAlreadyExistsError):
                raise errors.UserAlreadyExistsError(
                    f"`{name}` already exists; skipping."
                )
        else:
            raise errors.UserTypeError.from_ctx(
                ctx,
                f"`{name}` already exists.",
                traceback=self.get_traceback(),
            )

        return mif

    def visitPindef_stmt(
        self, ctx: ap.Pindef_stmtContext
    ) -> KeyOptMap[L.ModuleInterface]:
        return self.visitPin_stmt(ctx.pin_stmt(), declaration=False)

    def visitPin_declaration(
        self, ctx: ap.Pin_declarationContext
    ) -> KeyOptMap[L.ModuleInterface]:
        return self.visitPin_stmt(ctx.pin_stmt(), declaration=True)

    def visitPin_stmt(
        self, ctx: ap.Pin_stmtContext, declaration: bool
    ) -> KeyOptMap[L.ModuleInterface]:
        if ctx.name():
            name = self.visitName(ctx.name())
        elif ctx.number_hint_natural():
            name = f"{self.visitNumber_hint_natural(ctx.number_hint_natural())}"
        elif ctx.string():
            name = self.visitString(ctx.string())
        else:
            raise ValueError(f"Unhandled pin name type `{ctx}`")

        ref = FieldRef(parts=[], pin=name).last
        if declaration:
            if mif := self._get_mif_and_warn_when_exists(ref, ctx):
                return KeyOptMap.from_item(
                    KeyOptItem.from_kv(TypeRef.from_one(name), mif)
                )
        else:
            try:
                mif = self.resolve_node(self._current_node, ref)
            except AttributeError:
                pass
            else:
                return KeyOptMap.from_item(
                    KeyOptItem.from_kv(TypeRef.from_one(name), mif)
                )

        if shims_t := self._current_node.try_get_trait(_has_ato_cmp_attrs):
            mif = shims_t.add_pin(name, ref.name)
            return KeyOptMap.from_item(KeyOptItem.from_kv(TypeRef.from_one(name), mif))

        raise errors.UserTypeError.from_ctx(
            ctx,
            f"Can't declare pins on components of type {self._current_node}",
            traceback=self.get_traceback(),
        )

    def visitSignaldef_stmt(
        self, ctx: ap.Signaldef_stmtContext
    ) -> KeyOptMap[L.ModuleInterface]:
        name = self.visitName(ctx.name())
        # TODO: @v0.4: remove this protection
        if mif := self._get_mif_and_warn_when_exists(ReferencePartType(name), ctx):
            return KeyOptMap.from_item(KeyOptItem.from_kv(TypeRef.from_one(name), mif))

        mif = self._current_node.add(F.Electrical(), name=name)
        return KeyOptMap.from_item(KeyOptItem.from_kv(TypeRef.from_one(name), mif))

    def _connect(
        self, a: L.ModuleInterface, b: L.ModuleInterface, ctx: ParserRuleContext | None
    ):
        """
        FIXME: In ato, we allowed duck-typing of connectables
        We need to reconcile this with the strong typing
        in faebryk's connect method
        For now, we'll attempt to connect by name, and log a deprecation
        warning if that succeeds, else, re-raise the exception emitted
        by the connect method
        """
        # If we're attempting to connect an Electrical to a SignalElectrical
        # (or ElectricLogic) then allow the connection, but issue a warning
        if pair := is_type_pair(a, b, F.Electrical, F.ElectricSignal):
            pair[0].connect(pair[1].line)

            # TODO: @v0.4 remove this deprecated import form
            with downgrade(errors.UserTypeError):
                a, b = pair
                a_type = a.__class__.__name__
                b_type = b.__class__.__name__
                raise errors.UserTypeError.from_ctx(
                    ctx,
                    f"Connected `{a}` (type {a_type}) to "
                    f"`{b}.line`, because `{b}` is an `{b_type}`. "
                    "This means that the reference isn't also connected through.",
                    traceback=self.get_traceback(),
                )

        else:
            try:
                # Try a proper connection
                a.connect(b)

            except NodeException as top_ex:
                top_ex = errors.UserNodeException.from_node_exception(
                    top_ex, ctx, self.get_traceback()
                )

                # If that fails, try connecting via duck-typing
                for name, (c_a, c_b) in a.zip_children_by_name_with(
                    b, L.ModuleInterface
                ).items():
                    if c_a is None:
                        if has_attr_or_property(a, name):
                            c_a = getattr(a, name)
                        else:
                            raise top_ex

                    if c_b is None:
                        if has_attr_or_property(b, name):
                            c_b = getattr(b, name)
                        else:
                            raise top_ex

                    try:
                        self._connect(c_a, c_b, None)
                    except NodeException:
                        raise top_ex

                else:
                    # If we connect everything via name (and tried in the first place)
                    # then we're good to go! We just need to tell everyone to probably
                    # not do that in the future - and we're off!
                    if (
                        ctx is not None
                    ):  # Check that this is the top-level _connect call
                        # TODO: @v0.4 increase the level of this to WARNING
                        # when there's an alternative
                        with downgrade(DeprecatedException, to_level=logging.DEBUG):
                            raise DeprecatedException.from_ctx(
                                ctx,
                                f"Connected `{a}` to `{b}` by duck-typing."
                                "They should be of the same type.",
                                traceback=self.get_traceback(),
                            )

    def visitConnect_stmt(self, ctx: ap.Connect_stmtContext):
        """Connect interfaces together"""
        connectables = [self.visitMif(c) for c in ctx.mif()]
        for err_cltr, (a, b) in iter_through_errors(
            itertools.pairwise(connectables),
            errors._BaseBaseUserException,
            SkipPriorFailedException,
        ):
            with err_cltr():
                self._connect(a, b, ctx)

        return NOTHING

    def visitDirected_connect_stmt(self, ctx: ap.Directed_connect_stmtContext):
        """Connect interfaces via bridgeable modules"""
        self._ensure_feature_enabled(ctx, _FeatureFlags.Feature.BRIDGE_CONNECT)

        bridgeables = [self.visitBridgeable(c) for c in ctx.bridgeable()]

        if bool(ctx.LSPERM()) and bool(ctx.SPERM()):
            raise errors.UserSyntaxError.from_ctx(
                ctx,
                "Only one type of connection direction per statement allowed",
                traceback=self.get_traceback(),
            )

        # reverse direction
        if bool(ctx.LSPERM()):
            bridgeables.reverse()

        head = None
        tail = None
        if isinstance(bridgeables[-1], L.ModuleInterface):
            tail = bridgeables[-1]
            bridgeables = bridgeables[:-1]

        if isinstance(bridgeables[0], L.ModuleInterface):
            head = bridgeables[0]
        else:
            head = bridgeables[0].get_trait(F.can_bridge).get_out()
        bridgeables = bridgeables[1:]

        for b in bridgeables:
            if not isinstance(b, L.Module):
                raise errors.UserTypeError.from_ctx(
                    ctx,
                    f"Can't bridge via `{b}` because it is not a `Module`",
                    traceback=self.get_traceback(),
                )

        try:
            head.connect_via(bridgeables, *([tail] if tail else []))
        except NodeException as ex:
            raise errors.UserNodeException.from_node_exception(
                ex, ctx, self.get_traceback()
            )

        return NOTHING

    def visitConnectable(
        self, ctx: ap.ConnectableContext
    ) -> L.Module | L.ModuleInterface:
        if def_stmt := ctx.pindef_stmt() or ctx.signaldef_stmt():
            (_, mif), *_ = self.visit(def_stmt)
            return mif
        elif field_ref := ctx.field_reference():
            ref = self.visitFieldReference(field_ref)
            node = self._get_referenced_node(ref, field_ref)
            if not isinstance(node, L.ModuleInterface) and not (
                isinstance(node, L.Module) and node.has_trait(F.can_bridge)
            ):
                raise TypeError(
                    node,
                    f"Can't connect `{node}` because it's not a `ModuleInterface`"
                    f" or `Module` with `can_bridge` trait",
                )
            return node
        else:
            raise NotImplementedError(f"Unhandled connectable type `{ctx}`")

    def visitMif(self, ctx: ap.MifContext) -> L.ModuleInterface:
        """Return the mif object of the connectable object."""
        try:
            connectable = self.visitConnectable(ctx.connectable())
        except TypeError as ex:
            raise errors.UserTypeError.from_ctx(
                ctx,
                f"Can't connect {ex.args[0]} because it's not a `ModuleInterface`",
                traceback=self.get_traceback(),
            ) from ex
        if isinstance(connectable, L.ModuleInterface):
            return connectable
        else:
            raise errors.UserTypeError.from_ctx(
                ctx,
                f"Can't connect `{connectable}` because it's not a `ModuleInterface`",
                traceback=self.get_traceback(),
            )

    def visitBridgeable(
        self, ctx: ap.BridgeableContext
    ) -> L.Module | L.ModuleInterface:
        try:
            return self.visitConnectable(ctx.connectable())
        except TypeError as ex:
            node = ex.args[0]
            if isinstance(node, L.Module):
                raise errors.UserTypeError.from_ctx(
                    ctx,
                    f"Can't connect `{node}` because it's not bridgeable "
                    "(needs `can_bridge` trait)",
                    traceback=self.get_traceback(),
                ) from ex
            else:
                raise errors.UserTypeError.from_ctx(
                    ctx,
                    str(ex),
                    traceback=self.get_traceback(),
                ) from ex

    def visitRetype_stmt(self, ctx: ap.Retype_stmtContext):
        from_ref = self.visitFieldReference(ctx.field_reference())
        to_ref = self.visitTypeReference(ctx.type_reference())
        from_node = self._get_referenced_node(from_ref, ctx)

        from_dsl_orig = from_node.try_get_trait(from_dsl)

        # Only Modules can be specialized (since they're the only
        # ones with specialization gifs).
        # TODO: consider duck-typing this
        if not isinstance(from_node, L.Module):
            raise errors.UserTypeError.from_ctx(
                ctx,
                f"Can't specialize `{from_node}` because it's not a `Module`",
                traceback=self.get_traceback(),
            )

        # TODO: consider extending this w/ the ability to specialize to an instance
        class_ = self._get_referenced_class(ctx, to_ref)
        with self._traceback_stack.enter(ctx):
            # TOOD: update definition
            with self._init_node(class_) as specialized_node:
                pass

        if not isinstance(specialized_node, L.Module):
            raise errors.UserTypeError.from_ctx(
                ctx,
                f"Can't specialize with `{specialized_node}`"
                " because it's not a `Module`",
                traceback=self.get_traceback(),
            )

        # FIXME: this is an abuse of disconnect_parent. The graph isn't intended to be
        # mutable like this, and it existed only for use in traits, however the
        # alternatives I could come up with were worse:
        # - an isinstance check to additionally run `get_most_special` on Modules +
        #   more processing down the line when we want the full name of the node
        # This is only be applied when specializing to a whole class, not an instance
        try:
            parent_deets = from_node.get_parent()
            # We use from_node.get_name() rather than from_ref[-1] because we can
            # ensure this reuses the exact name after any normalization
            from_node_name = from_node.get_name()
            assert parent_deets is not None, (
                "uhh not sure how you get here without trying to replace the root node,"
                " which you shouldn't ever have access to"
            )
            parent, _ = parent_deets
            from_node.parent.disconnect_parent()
            assert isinstance(parent, L.Module)

            # We have to make sure the from_node was part of the runtime attrs
            if not any(r is from_node for r in parent.runtime.values()):
                raise errors.UserNotImplementedError.from_ctx(
                    ctx,
                    "We cannot properly specialize nodes within the base definition of"
                    " a module. This limitation mostly applies to fabll modules today.",
                    traceback=self.get_traceback(),
                )

            # Now, slot that badboi back in right where it's less-special brother's spot
            del parent.runtime[from_node_name]
            parent.add(specialized_node, name=from_node_name)

            try:
                from_node.specialize(specialized_node)
            except* L.Module.InvalidSpecializationError as ex:
                raise errors.UserException.from_ctx(
                    ctx,
                    f"Can't specialize `{from_ref}` with `{to_ref}`:\n"
                    + "\n".join(f" - {e.message}" for e in ex.exceptions),
                    traceback=self.get_traceback(),
                ) from ex
        except Exception:
            # TODO: skip further errors about this node w/ self._record_failed_node()
            raise

        from_dsl_ = specialized_node.add(from_dsl(src_ctx=ctx.type_reference()))
        if from_dsl_orig is not None:
            from_dsl_.references.extend(from_dsl_orig.references)

        from_dsl_.set_definition(class_)
        from_dsl_.add_reference(ctx.field_reference())

        return NOTHING

    def visitBlockdef(self, ctx: ap.BlockdefContext):
        """Do nothing. Handled in Surveyor."""
        return NOTHING

    def visitImport_stmt(self, ctx: ap.Import_stmtContext):
        """Do nothing. Handled in Surveyor."""
        return NOTHING

    def visitDep_import_stmt(self, ctx: ap.Dep_import_stmtContext):
        """Do nothing. Handled in Surveyor."""
        return NOTHING

    def visitAssert_stmt(self, ctx: ap.Assert_stmtContext):
        comparisons = [c for _, c in self.visitComparison(ctx.comparison())]
        for cmp in comparisons:
            if isinstance(cmp, BoolSet):
                if not cmp:
                    raise errors.UserAssertionError.from_ctx(
                        ctx,
                        "Assertion failed",
                        traceback=self.get_traceback(),
                    )
            elif isinstance(cmp, ConstrainableExpression):
                cmp.constrain()
            else:
                raise ValueError(f"Unhandled comparison type {type(cmp)}")
        return NOTHING

    def _get_trait_constructor(
        self, ctx: ap.Trait_stmtContext, ref: TypeRef, constructor_name: str | None
    ) -> tuple[type[L.Trait], Callable, tuple[Type | None]]:
        try:
            trait_cls = self._get_referenced_class(ctx, ref)
        except errors.UserKeyError as ex:
            raise errors.UserTraitNotFoundError.from_ctx(
                ctx,
                f"No such trait: `{ref}`",
                traceback=self.get_traceback(),
            ) from ex

        if isinstance(trait_cls, ap.BlockdefContext) or not issubclass(
            trait_cls, L.Trait
        ):
            raise errors.UserInvalidTraitError.from_ctx(
                ctx,
                f"`{ref}` is not a valid trait",
                traceback=self.get_traceback(),
            )

        constructor = trait_cls
        args = tuple()

        if constructor_name is not None:
            try:
                attr = inspect.getattr_static(trait_cls, constructor_name)
            except AttributeError:
                raise errors.UserTraitNotFoundError.from_ctx(
                    ctx,
                    f"No such trait constructor: `{ref}:{constructor_name}`",
                    traceback=self.get_traceback(),
                )

            if not isinstance(attr, classmethod):
                raise errors.UserInvalidTraitError.from_ctx(
                    ctx,
                    f"`{ref}:{constructor_name}` is not a valid trait constructor",
                    traceback=self.get_traceback(),
                )

            if inspect.signature(attr.__func__).return_annotation not in (
                typing.Self,
                trait_cls,
                trait_cls.__name__,
            ):
                raise errors.UserInvalidTraitError.from_ctx(
                    ctx,
                    f"`{ref}:{constructor_name}` is not a valid trait constructor "
                    "(missing or invalid return type annotation)",
                    traceback=self.get_traceback(),
                )

            constructor = attr.__func__
            args = (trait_cls,)

        return trait_cls, constructor, args

    def visitTrait_stmt(self, ctx: ap.Trait_stmtContext):
        self._ensure_feature_enabled(ctx, _FeatureFlags.Feature.TRAITS)

        ref = self.visitTypeReference(ctx.type_reference())
        constructor_name = (
            self.visitName(ctx.constructor().name())
            if ctx.constructor() is not None
            else None
        )
        trait_name = f"{ref}{f'::{constructor_name}' if constructor_name else ''}"
        trait_cls, constructor, args = self._get_trait_constructor(
            ctx, ref, constructor_name
        )
        kwargs = self.visitTemplate(ctx.template())

        callable_ = getattr(constructor, "__original_init__", constructor)
        constructor_signature = inspect.signature(callable_)

        for arg_name, arg_value in kwargs.items():
            if arg_name not in constructor_signature.parameters:
                raise errors.UserBadParameterError.from_ctx(
                    ctx,
                    f"Unknown template argument `{arg_name}` for `{trait_name}`",
                    traceback=self.get_traceback(),
                )

            if isinstance(arg_value, str):
                try:
                    kwargs[arg_name] = _try_upgrade_str_to_enum(
                        callable_, arg_name, arg_value
                    )
                except _EnumUpgradeError as ex:
                    raise errors.UserInvalidValueError.from_ctx(
                        enum_types=ex.enum_types,
                        enum_name=arg_name,
                        value=arg_value,
                        origin=ctx,
                        traceback=self.get_traceback(),
                    ) from ex

        try:
            trait = constructor(*args, **kwargs)
        except Exception as e:
            exc_str = f": {e}" if str(e) else ""
            raise errors.UserTraitError.from_ctx(
                ctx,
                f"Error applying trait `{trait_name}`{exc_str}",
                traceback=self.get_traceback(),
            ) from e

        self._current_node.add(trait)

        from_dsl_ = trait.add(
            type_from_dsl(
                src_ctx=ctx.type_reference(),
                name=str(ref),
                definition_ctx=trait_cls,
                category="trait",
            )
        )
        from_dsl_.add_reference(ctx.type_reference())

        return NOTHING

    # Returns fab_param.ConstrainableExpression or BoolSet
    def visitComparison(
        self, ctx: ap.ComparisonContext
    ) -> KeyOptMap[ConstrainableExpression | BoolSet]:
        exprs = [
            self.visitArithmetic_expression(c)
            for c in [ctx.arithmetic_expression()]
            + [cop.getChild(0).arithmetic_expression() for cop in ctx.compare_op_pair()]
        ]
        op_strs = [
            cop.getChild(0).getChild(0).getText() for cop in ctx.compare_op_pair()
        ]

        predicates = []
        for (lh, rh), op_str in zip(itertools.pairwise(exprs), op_strs):
            match op_str:
                # @v0.4 upgrade to error
                case "<":
                    with downgrade(
                        errors.UserNotImplementedError, to_level=logging.WARNING
                    ):
                        raise errors.UserNotImplementedError.from_ctx(
                            ctx,
                            "`<` is not supported. Use `<=` instead.",
                            traceback=self.get_traceback(),
                        )
                    op = LessOrEqual
                case ">":
                    with downgrade(
                        errors.UserNotImplementedError, to_level=logging.WARNING
                    ):
                        raise errors.UserNotImplementedError.from_ctx(
                            ctx,
                            "`>` is not supported. Use `>=` instead.",
                            traceback=self.get_traceback(),
                        )
                    op = GreaterOrEqual
                case "<=":
                    op = LessOrEqual
                case ">=":
                    op = GreaterOrEqual
                case "within":
                    op = IsSubset
                case "is":
                    op = Is
                case _:
                    # We shouldn't be able to get here with parseable input
                    raise ValueError(f"Unhandled operator `{op_str}`")

            # TODO: should we be reducing here to a series of ANDs?
            predicates.append(op(lh, rh))

        return KeyOptMap([KeyOptItem.from_kv(None, p) for p in predicates])

    def visitArithmetic_expression(
        self, ctx: ap.Arithmetic_expressionContext
    ) -> Numeric:
        if ctx.OR_OP() or ctx.AND_OP():
            raise errors.UserTypeError.from_ctx(
                ctx,
                "Logical operations are not supported",
                traceback=self.get_traceback(),
            )
            lh = self.visitArithmetic_expression(ctx.arithmetic_expression())
            rh = self.visitSum(ctx.sum_())

            if ctx.OR_OP():
                return operator.or_(lh, rh)
            else:
                return operator.and_(lh, rh)

        return self.visitSum(ctx.sum_())

    def visitSum(self, ctx: ap.SumContext) -> Numeric:
        if ctx.PLUS() or ctx.MINUS():
            lh = self.visitSum(ctx.sum_())
            rh = self.visitTerm(ctx.term())

            if ctx.PLUS():
                return operator.add(lh, rh)
            else:
                return operator.sub(lh, rh)

        return self.visitTerm(ctx.term())

    def visitTerm(self, ctx: ap.TermContext) -> Numeric:
        if ctx.STAR() or ctx.DIV():
            lh = self.visitTerm(ctx.term())
            rh = self.visitPower(ctx.power())

            if ctx.STAR():
                return operator.mul(lh, rh)
            else:
                return operator.truediv(lh, rh)

        return self.visitPower(ctx.power())

    def visitPower(self, ctx: ap.PowerContext) -> Numeric:
        if ctx.POWER():
            base, exp = map(self.visitFunctional, ctx.functional())
            return operator.pow(base, exp)
        else:
            return self.visitFunctional(ctx.functional(0))

    def visitFunctional(self, ctx: ap.FunctionalContext) -> Numeric:
        if ctx.name():
            name = self.visitName(ctx.name())
            operands = [self.visitBound(b) for b in ctx.bound()]
            if name == "min":
                return Min(*operands)
            elif name == "max":
                return Max(*operands)
            else:
                raise errors.UserNotImplementedError.from_ctx(
                    ctx, f"Unknown function `{name}`"
                )
        else:
            return self.visitBound(ctx.bound(0))

    def visitBound(self, ctx: ap.BoundContext) -> Numeric:
        return self.visitAtom(ctx.atom())

    def visitAtom(self, ctx: ap.AtomContext) -> Numeric:
        if ctx.field_reference():
            ref = self.visitFieldReference(ctx.field_reference())
            target = self._get_referenced_node(ref.stem, ctx)
            return self._get_param(target, ref.last, ctx)

        elif ctx.literal_physical():
            return self.visitLiteral_physical(ctx.literal_physical())

        elif group_ctx := ctx.arithmetic_group():
            assert isinstance(group_ctx, ap.Arithmetic_groupContext)
            return self.visitArithmetic_expression(group_ctx.arithmetic_expression())

        raise ValueError(f"Unhandled atom type `{ctx}`")

    def _get_unit_from_ctx(self, ctx: ParserRuleContext) -> UnitType:
        """Return a pint unit from a context."""
        unit_str = ctx.getText()
        try:
            return P.Unit(unit_str)
        except UndefinedUnitError as ex:
            raise errors.UserUnknownUnitError.from_ctx(
                ctx,
                f"Unknown unit `{unit_str}`",
                traceback=self.get_traceback(),
            ) from ex

    def visitLiteral_physical(
        self, ctx: ap.Literal_physicalContext
    ) -> Quantity_Interval:
        """Yield a physical value from a physical context."""
        if ctx.quantity():
            qty = self.visitQuantity(ctx.quantity())
            value = Single(qty)
        elif ctx.bilateral_quantity():
            value = self.visitBilateral_quantity(ctx.bilateral_quantity())
        elif ctx.bound_quantity():
            value = self.visitBound_quantity(ctx.bound_quantity())
        else:
            # this should be protected because it shouldn't be parseable
            raise ValueError
        return value

    def visitQuantity(self, ctx: ap.QuantityContext) -> Quantity:
        """Yield a physical value from an implicit quantity context."""
        raw: Number = self.visitNumber(ctx.number())
        if raw.base != 10:
            value = int(raw.value, raw.base)
        else:
            value = float(raw.value)

        if raw.negative:
            value = -value

        if unit_ctx := ctx.name():
            unit = self._get_unit_from_ctx(unit_ctx)
        else:
            unit = dimensionless

        return Quantity(value, unit)  # type: ignore

    def visitBilateral_quantity(
        self, ctx: ap.Bilateral_quantityContext
    ) -> Quantity_Interval:
        """Yield a physical value from a bilateral quantity context."""
        nominal_qty = self.visitQuantity(ctx.quantity())

        tol_ctx: ap.Bilateral_toleranceContext = ctx.bilateral_tolerance()
        raw_tol = self.visitNumber_signless(tol_ctx.number_signless())
        if raw_tol.base != 10:
            raise errors.UserSyntaxError.from_ctx(
                tol_ctx,
                "Tolerance must be a decimal number",
                traceback=self.get_traceback(),
            )
        tol_num = float(raw_tol.value)

        # Handle proportional tolerances
        if tol_ctx.PERCENT():
            tol_divider = 100
        elif tol_ctx.name() and tol_ctx.name().getText() == "ppm":
            tol_divider = 1e6
        else:
            tol_divider = None

        if tol_divider:
            if nominal_qty == 0:
                raise errors.UserException.from_ctx(
                    tol_ctx,
                    "Can't calculate tolerance percentage of a nominal value of zero",
                    traceback=self.get_traceback(),
                )

            # Calculate tolerance value from percentage/ppm
            tol_value = tol_num / tol_divider
            return Range.from_center_rel(nominal_qty, tol_value)

        # Ensure the tolerance has a unit
        if tol_name := tol_ctx.name():
            # In this case there's a named unit on the tolerance itself
            tol_qty = tol_num * self._get_unit_from_ctx(tol_name)
        elif nominal_qty.unitless:
            tol_qty = tol_num * dimensionless
        else:
            tol_qty = tol_num * nominal_qty.units

        # Ensure units on the nominal quantity
        if nominal_qty.unitless:
            nominal_qty = nominal_qty * HasUnit.get_units(tol_qty)

        # If the nominal has a unit, then we rely on the ranged value's unit compatibility # noqa: E501  # pre-existing
        if not nominal_qty.is_compatible_with(tol_qty):
            raise errors.UserTypeError.from_ctx(
                tol_name,
                f"Tolerance unit ({HasUnit.get_units(tol_qty)}) is not dimensionally"
                f" compatible with nominal unit ({nominal_qty.units})",
                traceback=self.get_traceback(),
            )

        return Range.from_center(nominal_qty, tol_qty)

    def visitBound_quantity(self, ctx: ap.Bound_quantityContext) -> Quantity_Interval:
        """Yield a physical value from a bound quantity context."""

        start, end = map(self.visitQuantity, ctx.quantity())

        # If only one of them has a unit, take the unit from the one which does
        if start.unitless and not end.unitless:
            start = start * end.units
        elif not start.unitless and end.unitless:
            end = end * start.units

        elif not start.is_compatible_with(end):
            # If they've both got units, let the RangedValue handle
            # the dimensional compatibility
            raise errors.UserTypeError.from_ctx(
                ctx,
                f"Tolerance unit ({end.units}) is not dimensionally"
                f" compatible with nominal unit ({start.units})",
                traceback=self.get_traceback(),
            )

        return Range(start, end)

    def visitCum_assign_stmt(self, ctx: ap.Cum_assign_stmtContext | Any):
        """
        Cumulative assignments can only be made on top of
        nothing (implicitly declared) or declared, but undefined values.

        Unlike assignments, they may not implicitly declare an attribute.
        """
        ref_dec = ctx.field_reference_or_declaration()
        assignee_ref = self.visitFieldReference(ref_dec.field_reference())
        target = self._get_referenced_node(assignee_ref, ctx)
        self.visitDeclaration_stmt(ref_dec.declaration_stmt())

        assignee = self._get_param(target, assignee_ref.last, ctx)
        value = self.visitCum_assignable(ctx.cum_assignable())

        # HACK: we have no way to check by what operator
        # the param is dynamically resolved
        # For now we assume any dynamic trait is sufficient
        if ctx.cum_operator().ADD_ASSIGN():
            assignee.alias_is(value)
        elif ctx.cum_operator().SUB_ASSIGN():
            assignee.alias_is(-value)
        else:
            # Syntax should protect from this
            raise ValueError(f"Unhandled set assignment operator {ctx}")

        # TODO: @v0.4 increase the level of this to WARNING
        # when there's an alternative
        with downgrade(DeprecatedException, to_level=logging.DEBUG):
            raise DeprecatedException(f"{ctx.cum_operator().getText()} is deprecated.")
        return NOTHING

    def visitSet_assign_stmt(self, ctx: ap.Set_assign_stmtContext):
        """
        Set cumulative assignments can only be made on top of
        nothing (implicitly declared) or declared, but undefined values.

        Unlike assignments, they may not implicitly declare an attribute.
        """
        ref_dec = ctx.field_reference_or_declaration()
        assignee_ref = self.visitFieldReference(ref_dec.field_reference())
        target = self._get_referenced_node(assignee_ref, ctx)
        self.visitDeclaration_stmt(ref_dec.declaration_stmt())

        assignee = self._get_param(target, assignee_ref.last, ctx)
        value = self.visitCum_assignable(ctx.cum_assignable())

        if ctx.OR_ASSIGN():
            assignee.constrain_superset(value)
        elif ctx.AND_ASSIGN():
            assignee.constrain_subset(value)
        else:
            # Syntax should protect from this
            raise ValueError(f"Unhandled set assignment operator {ctx}")

        # TODO: @v0.4 remove this deprecated import form
        with downgrade(DeprecatedException):
            lhs = ref_dec.field_reference().getText()
            rhs = ctx.cum_assignable().getText()
            if ctx.OR_ASSIGN():
                subset = lhs
                superset = rhs
            else:
                subset = rhs
                superset = lhs
            raise DeprecatedException(
                f"Set assignment of `{assignee}` is deprecated."
                f' Use "assert `{subset}` within `{superset}` "instead.'
            )
        return NOTHING

    def _try_get_unit_from_type_info(
        self, ctx: ap.Type_infoContext | None
    ) -> UnitType | None:
        if ctx is None:
            return None
        unit_ctx: ap.UnitContext = ctx.unit()
        if unit_ctx is None:
            return None
        # TODO: @v0.4.0: remove this shim
        unit = unit_ctx.getText()
        if unit in _declaration_domain_to_unit:
            unit = _declaration_domain_to_unit[unit]
            # TODO: consider deprecating this
        else:
            unit = self._get_unit_from_ctx(unit_ctx)

        return unit

    def _handleParameterDeclaration(
        self, ref: TypeRef, unit: UnitType, ctx: ParserRuleContext
    ):
        assert unit is not None, "Type info should be enforced by the parser"
        name = FieldRef.from_type_ref(ref).last
        param = self._ensure_param(self._current_node, name, unit, ctx)
        if param in self._param_assignments:
            declaration_after_definition = any(
                assignment.is_definition
                for assignment in self._param_assignments[param]
            )
            # TODO: @v0.4 remove this deprecated import form
            with downgrade(errors.UserKeyError):
                if declaration_after_definition:
                    raise errors.UserKeyError.from_ctx(
                        ctx,
                        f"Ignoring declaration of `{name}` "
                        "because it's already defined",
                        traceback=self.get_traceback(),
                    )
                else:
                    raise errors.UserKeyError.from_ctx(
                        ctx,
                        f"Ignoring redeclaration of `{name}`",
                        traceback=self.get_traceback(),
                    )
        else:
            self._param_assignments[param].append(
                _ParameterDefinition(
                    ref=FieldRef.from_type_ref(ref),
                    ctx=ctx,
                    traceback=self.get_traceback(),
                )
            )

    def visitDeclaration_stmt(self, ctx: ap.Declaration_stmtContext | None):
        """Handle declaration statements."""
        if ctx is None:
            return NOTHING
        ref = self.visitFieldReference(ctx.field_reference())
        if len(ref) > 1:
            raise errors.UserSyntaxError.from_ctx(
                ctx,
                f"Can't declare fields in a nested object `{ref}`",
                traceback=self.get_traceback(),
            )
        type_ref = ref.to_type_ref()
        if type_ref is None:
            raise errors.UserSyntaxError.from_ctx(
                ctx,
                f"Can't declare keyed attributes `{ref}`",
                traceback=self.get_traceback(),
            )

        # check declaration type
        unit = self._try_get_unit_from_type_info(ctx.type_info())
        if unit is not None:
            self._handleParameterDeclaration(type_ref, unit, ctx)
            return NOTHING

        assert False, "Only parameter declarations supported"

    def visitPass_stmt(self, ctx: ap.Pass_stmtContext):
        return NOTHING

    def visitSlice(self, ctx: ap.SliceContext | None) -> slice:
        """Parse slice components into a slice object."""
        if ctx is None:
            return slice(None)

        start, stop, step = None, None, None

        if (start_ctx := ctx.slice_start()) is not None:
            start = self.visitNumber_hint_integer(start_ctx.number_hint_integer())

        if (stop_ctx := ctx.slice_stop()) is not None:
            stop = self.visitNumber_hint_integer(stop_ctx.number_hint_integer())

        if (step_ctx := ctx.slice_step()) is not None:
            step = self.visitNumber_hint_integer(step_ctx.number_hint_integer())

        if step == 0:
            raise errors.UserValueError.from_ctx(
                ctx, "Slice step cannot be zero", traceback=self.get_traceback()
            )

        return slice(start, stop, step)

    def visitList_literal_of_field_references(
        self, ctx: ap.List_literal_of_field_referencesContext
    ) -> list[L.Node]:
        refs = [self.visitFieldReference(ref) for ref in ctx.field_reference()]
        out = []
        for ref in refs:
            try:
                out.append(self.resolve_node(self._current_node, ref))
            except TypeError as e:
                raise errors.UserTypeError.from_ctx(
                    ctx,
                    f"Invalid type ({complete_type_string(e.args[0])}) for "
                    f"list literal: `{ref}`. Expected `Module` or `ModuleInterface`.",
                    traceback=self.get_traceback(),
                )
        return out

    def visitIterable_references(
        self, ctx: ap.Iterable_referencesContext
    ) -> Iterable[L.Node]:
        if ref := ctx.field_reference():
            iterable_ref = self.visitFieldReference(ref)
            requested_slice = self.visitSlice(ctx.slice_())

            try:
                _iterable_node = self.resolve_node_field(
                    self._current_node, iterable_ref
                )
            except AttributeError as ex:
                raise errors.UserKeyError.from_ctx(
                    ref,
                    f"Cannot iterate over non-existing field `{iterable_ref}`:"
                    f"{str(ex)}",
                    traceback=self.get_traceback(),
                ) from ex

            # Prepare the iterable list
            iterable_node: list[L.Node] | None = None
            if isinstance(_iterable_node, list):
                iterable_node = list(_iterable_node)
            elif isinstance(_iterable_node, set):
                # Convert set to list for deterministic order & slicing
                iterable_node = sorted(list(_iterable_node), key=lambda n: n.get_name())
            elif isinstance(_iterable_node, dict):
                iterable_node = list(_iterable_node.values())

            if not isinstance(iterable_node, list) or not all(
                isinstance(item, L.Node) for item in iterable_node
            ):
                raise errors.UserTypeError.from_ctx(
                    ctx.field_reference(),
                    f"Cannot iterate over type `{complete_type_string(_iterable_node)}`"
                    f". Expected `list[Node]`, `dict[str, Node]` or `set[Node]`"
                    f"  (e.g., from `new X[N]`).",
                    traceback=self.get_traceback(),
                )
        elif ref := ctx.list_literal_of_field_references():
            iterable_node = self.visitList_literal_of_field_references(ref)
            requested_slice = slice(None)
        else:
            raise errors.UserNotImplementedError.from_ctx(
                ctx,
                "Unsupported iterable reference",
                traceback=self.get_traceback(),
            )

        # Apply slice
        try:
            final_iterable = iterable_node[requested_slice]
        except ValueError as ex:
            # e.g. slice step cannot be zero
            raise errors.UserValueError.from_ctx(
                ctx.slice_(),
                f"Invalid slice parameters: {ex}",
                traceback=self.get_traceback(),
            ) from ex

        return final_iterable

    def visitFor_stmt(self, ctx: ap.For_stmtContext):
        self._ensure_feature_enabled(ctx, _FeatureFlags.Feature.FOR_LOOP)

        # Handle for loops.
        if self._in_for_loop:
            raise errors.UserSyntaxError.from_ctx(
                ctx,
                "Nested for loops are not currently supported.",
                traceback=self.get_traceback(),
            )

        self._in_for_loop = True
        try:
            loop_var_name = self.visitName(ctx.name())

            iterable = self.visitIterable_references(ctx.iterable_references())
            block_ctx = ctx.block()  # Define block_ctx here

            # Check for variable name collisions before starting the loop
            try:
                self.resolve_node_property(self._current_node, loop_var_name)
            except AttributeError:
                pass
            else:
                raise errors.UserKeyError.from_ctx(
                    ctx.name(),
                    f"Loop variable '{loop_var_name}' conflicts with an existing"
                    f" attribute or runtime variable.",
                    traceback=self.get_traceback(),
                )

            # Loop and manage scope temporarily using runtime dict
            try:
                for item in iterable:
                    self._current_node.runtime[loop_var_name] = item
                    self.visitBlock(block_ctx)
            finally:
                # Ensure cleanup even if visitBlock raises an error
                if loop_var_name in self._current_node.runtime:
                    del self._current_node.runtime[loop_var_name]
                # Note: We don't restore original_value because the initial check
                #  ensures it was NOTHING.

        finally:
            self._in_for_loop = False

        return NOTHING

    def visitLiteral(self, ctx: ap.LiteralContext) -> Any:
        if (string_ctx := ctx.string()) is not None:
            return self.visitString(string_ctx)
        elif (boolean_ctx := ctx.boolean_()) is not None:
            return self.visitBoolean_(boolean_ctx)
        else:
            return self.visitNumber(ctx.number()).interpret()

    def visitTemplate_arg(self, ctx: ap.Template_argContext) -> tuple[str, Any]:
        return ctx.name().getText(), self.visitLiteral(ctx.literal())

    def visitTemplate(self, ctx: ap.TemplateContext | None) -> dict[str, Any]:
        if ctx is None:
            return {}

        kwargs = {
            k: v for k, v in (self.visitTemplate_arg(arg) for arg in ctx.template_arg())
        }

        return kwargs


bob = Bob()
