"""
Build faebryk core objects from ato DSL.

TODO:
- [ ] Handle units
- [ ] Implement a __deepcopy__ method for the Node class to slowly re-walking the AST
"""

import collections
import importlib
import logging
import operator
import sys
import warnings
from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from itertools import chain
from pathlib import Path
from typing import (
    Any,
    Iterable,
    Iterator,
    Self,
    Type,
)

import faebryk.library._F as F
import faebryk.libs.library.L as L
import pint
from antlr4 import ParserRuleContext
from faebryk.core.trait import Trait
from faebryk.libs.exceptions import FaebrykException
from faebryk.libs.util import FuncDict

from atopile import address, config, errors, expressions, parse_utils
from atopile.address import AddrStr
from atopile.datatypes import KeyOptItem, KeyOptMap, StackList
from atopile.expressions import RangedValue
from atopile.front_end import _get_unit_from_ctx
from atopile.parse import parser
from atopile.parse_utils import get_src_info_from_ctx
from atopile.parser.AtopileParser import AtopileParser as ap
from atopile.parser.AtopileParserVisitor import AtopileParserVisitor

from atopile.datatypes import Ref

log = logging.getLogger(__name__)


class BasicsMixin:
    def visitName(self, ctx: ap.NameContext) -> str:
        """
        If this is an int, convert it to one (for pins), else return the name as a string.
        """
        return ctx.getText()

    def visitAttr(self, ctx: ap.AttrContext) -> list[str]:
        return [self.visitName(name) for name in ctx.name()]

    def visitName_or_attr(self, ctx: ap.Name_or_attrContext) -> list[str]:
        if ctx.name():
            return [self.visitName(ctx.name())]
        elif ctx.attr():
            return self.visitAttr(ctx.attr())

        raise errors.AtoError.from_ctx(ctx, "Expected a name or attribute")

    def visitString(self, ctx: ap.StringContext) -> str:
        raw: str = ctx.getText()
        return raw.strip("\"'")

    def visitBoolean_(self, ctx: ap.Boolean_Context) -> bool:
        raw: str = ctx.getText()

        if raw.lower() == "true":
            return True
        elif raw.lower() == "false":
            return False

        raise errors.AtoError.from_ctx(ctx, f"Expected a boolean value, got {raw}")


class PhysicalValuesMixin:
    def visitLiteral_physical(self, ctx: ap.Literal_physicalContext) -> RangedValue:
        """Yield a physical value from a physical context."""
        if ctx.quantity():
            return self.visitQuantity(ctx.quantity())
        if ctx.bilateral_quantity():
            return self.visitBilateral_quantity(ctx.bilateral_quantity())
        if ctx.bound_quantity():
            return self.visitBound_quantity(ctx.bound_quantity())

        raise ValueError  # this should be protected because it shouldn't be parseable

    def visitQuantity(self, ctx: ap.QuantityContext) -> RangedValue:
        """Yield a physical value from an implicit quantity context."""
        raw: str = ctx.NUMBER().getText()
        if raw.startswith("0x"):
            value = int(raw, 16)
        else:
            value = float(raw)

        # Ignore the positive unary operator
        if ctx.MINUS():
            value = -value

        if ctx.name():
            unit = _get_unit_from_ctx(ctx.name())
        else:
            unit = pint.Unit("")

        value = RangedValue(
            val_a=value,
            val_b=value,
            unit=unit,
            str_rep=parse_utils.reconstruct(ctx),
            # We don't bother with other formatting info here
            # because it's not used for un-toleranced values
        )
        setattr(value, "src_ctx", ctx)
        return value

    def visitBilateral_quantity(self, ctx: ap.Bilateral_quantityContext) -> RangedValue:
        """Yield a physical value from a bilateral quantity context."""
        nominal_quantity = self.visitQuantity(ctx.quantity())

        tol_ctx: ap.Bilateral_toleranceContext = ctx.bilateral_tolerance()
        tol_num = float(tol_ctx.NUMBER().getText())

        # Handle proportional tolerances
        if tol_ctx.PERCENT():
            tol_divider = 100
        elif tol_ctx.name() and tol_ctx.name().getText() == "ppm":
            tol_divider = 1e6
        else:
            tol_divider = None

        if tol_divider:
            if nominal_quantity == 0:
                raise errors.AtoError.from_ctx(
                    tol_ctx,
                    "Can't calculate tolerance percentage of a nominal value of zero",
                )

            # In this case, life's a little easier, and we can simply multiply the nominal
            value = RangedValue(
                val_a=nominal_quantity.min_val
                - (nominal_quantity.min_val * tol_num / tol_divider),
                val_b=nominal_quantity.max_val
                + (nominal_quantity.max_val * tol_num / tol_divider),
                unit=nominal_quantity.unit,
                str_rep=parse_utils.reconstruct(ctx),
            )
            setattr(value, "src_ctx", ctx)
            return value

        # Handle tolerances with units
        if tol_ctx.name():
            # In this case there's a named unit on the tolerance itself
            # We need to make sure it's dimensionally compatible with the nominal
            tol_quantity = RangedValue(
                -tol_num, tol_num, _get_unit_from_ctx(tol_ctx.name()), tol_ctx
            )

            # If the nominal has no unit, then we take the unit's tolerance for the nominal
            if nominal_quantity.unit == pint.Unit(""):
                value = RangedValue(
                    val_a=nominal_quantity.min_val + tol_quantity.min_val,
                    val_b=nominal_quantity.max_val + tol_quantity.max_val,
                    unit=tol_quantity.unit,
                    str_rep=parse_utils.reconstruct(ctx),
                )
                setattr(value, "src_ctx", ctx)
                return value

            # If the nominal has a unit, then we rely on the ranged value's unit compatibility
            try:
                return nominal_quantity + tol_quantity
            except pint.DimensionalityError as ex:
                raise errors.AtoTypeError.from_ctx(
                    tol_ctx.name(),
                    f"Tolerance unit '{tol_quantity.unit}' is not dimensionally"
                    f" compatible with nominal unit '{nominal_quantity.unit}'",
                ) from ex

        # If there's no unit or percent, then we have a simple tolerance in the same units
        # as the nominal
        value = RangedValue(
            val_a=nominal_quantity.min_val - tol_num,
            val_b=nominal_quantity.max_val + tol_num,
            unit=nominal_quantity.unit,
            str_rep=parse_utils.reconstruct(ctx),
        )
        setattr(value, "src_ctx", ctx)
        return value

    def visitBound_quantity(self, ctx: ap.Bound_quantityContext) -> RangedValue:
        """Yield a physical value from a bound quantity context."""

        start = self.visitQuantity(ctx.quantity(0))
        assert start.tolerance == 0
        end = self.visitQuantity(ctx.quantity(1))
        assert end.tolerance == 0

        # If only one of them has a unit, take the unit from the one which does
        if (start.unit == pint.Unit("")) ^ (end.unit == pint.Unit("")):
            if start.unit == pint.Unit(""):
                known_unit = end.unit
            else:
                known_unit = start.unit

            value = RangedValue(
                val_a=start.min_val,
                val_b=end.min_val,
                unit=known_unit,
                str_rep=parse_utils.reconstruct(ctx),
            )
            setattr(value, "src_ctx", ctx)
            return value

        # If they've both got units, let the RangedValue handle
        # the dimensional compatibility
        try:
            value = RangedValue(
                val_a=start.min_qty,
                val_b=end.min_qty,
                str_rep=parse_utils.reconstruct(ctx),
            )
            setattr(value, "src_ctx", ctx)
            return value
        except pint.DimensionalityError as ex:
            raise errors.AtoTypeError.from_ctx(
                ctx,
                f"Tolerance unit '{end.unit}' is not dimensionally"
                f" compatible with nominal unit '{start.unit}'",
            ) from ex


class NOTHING:
    """A sentinel object to represent a "nothing" return value."""


class SequenceMixin(AtopileParserVisitor):
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
            for err_cltr, child in errors.iter_through_errors(children):
                with err_cltr():
                    child_result = self.visit(child)
                    if child_result is not NOTHING:
                        yield child_result

        child_results = chain.from_iterable(_visit())
        child_results = filter(lambda x: x is not NOTHING, child_results)
        child_results = KeyOptMap(KeyOptItem(cr) for cr in child_results)

        return KeyOptMap(child_results)

    def visitStmt(self, ctx: ap.StmtContext) -> None:
        """
        Ensure consistency of return type.
        We choose to raise any below exceptions here, because stmts can be nested,
        and raising exceptions serves as our collection mechanism.
        """
        if ctx.simple_stmts():
            stmt_returns = self.visitSimple_stmts(ctx.simple_stmts())
            return stmt_returns
        elif ctx.compound_stmt():
            item = self.visit(ctx.compound_stmt())
            if item is NOTHING:
                return KeyOptMap.empty()
            assert isinstance(item, KeyOptItem)
            return KeyOptMap.from_item(item)

        raise TypeError("Unexpected statement type")

    def visitSimple_stmts(self, ctx: ap.Simple_stmtsContext) -> KeyOptMap:
        return self.visit_iterable_helper(ctx.simple_stmt())

    def visitBlock(self, ctx: ap.BlockContext) -> KeyOptMap:
        if ctx.stmt():
            return self.visit_iterable_helper(ctx.stmt())
        if ctx.simple_stmts():
            return self.visitSimple_stmts(ctx.simple_stmts())

        raise ValueError  # this should be protected because it shouldn't be parseable


class BlockNotFoundError(errors.AtoKeyError):
    """
    Raised when a block doesn't exist.
    """


@contextmanager
def _contextualize_errors(
    ctx: ParserRuleContext,
    error_types: tuple[Type[errors.AtoError]] | Type[errors.AtoError],
):
    if not isinstance(error_types, tuple):
        error_types = (error_types,)

    try:
        yield
    except error_types as ex:
        raise type(ex).from_ctx(ctx, *ex.args) from ex


def _src_location_str(ctx: ParserRuleContext) -> str:
    """Return a string representation of a source location."""
    file, line, col, *_ = get_src_info_from_ctx(ctx)
    return f"{file}:{line}:{col}"


@contextmanager
def _sys_path_context(path: Path):
    """Add a path to the system path for the duration of the context."""
    sys.path.append(path)
    try:
        yield
    finally:
        sys.path.remove(path)


class _DictyModule(collections.abc.Mapping):
    """A wrapper around a Node that makes it look like a dict."""

    def __init__(self, node: L.Node) -> None:
        self._node = node

    def __iter__(self) -> Iterator[str]:
        for child in self._node.get_children(types=L.Node):
            assert isinstance(child, L.Node)
            yield child.get_name()

    def __len__(self) -> int:
        return len(self._node.get_children(types=L.Node))

    def __getitem__(self, key: str) -> L.Node:
        for child in self._node.get_children(types=L.Node):
            assert isinstance(child, L.Node)
            if child.get_name() == key:
                return child

        raise errors.AtoKeyError(f"No attribute '{key}' found on {self._node}")

    @classmethod
    def from_module(cls, module: L.Module) -> Self:
        return cls(module.get_most_special())


class from_dsl(Trait.decless()):
    def __init__(self, src_ctx: ParserRuleContext) -> None:
        super().__init__()
        self.src_ctx = src_ctx


@dataclass
class Context:
    """Context dataclass for the visitor constructor."""

    @dataclass
    class ImportPlaceholder:
        ref: list[str]
        from_path: str
        original_ctx: ParserRuleContext

    file_path: Path
    scope_ctx: ParserRuleContext
    refs: dict[Ref, Type[L.Node] | ap.BlockdefContext | ImportPlaceholder]


class Surveyor(AtopileParserVisitor, BasicsMixin, SequenceMixin):
    def visitImport_stmt(
        self, ctx: ap.Import_stmtContext
    ) -> KeyOptMap[Context.ImportPlaceholder]:
        lazy_imports = [
            Context.ImportPlaceholder(
                ref=self.visitName_or_attr(ctx.name_or_attr()),
                from_path=self.visitString(string),
                original_ctx=ctx,
            )
            for string in ctx.string()
        ]
        return KeyOptMap(KeyOptItem(li.ref, li) for li in lazy_imports)

    def visitDep_import_stmt(
        self, ctx: ap.Dep_import_stmtContext
    ) -> KeyOptMap[Context.ImportPlaceholder]:
        lazy_import = Context.ImportPlaceholder(
            ref=self.visitName_or_attr(ctx.name_or_attr()),
            from_path=self.visitString(ctx.string()),
            original_ctx=ctx,
        )
        return KeyOptMap.from_item(KeyOptItem(lazy_import.ref, lazy_import))

    def visitBlockdef(self, ctx: ap.BlockdefContext) -> KeyOptMap:
        ref = self.visitName_or_attr(ctx.name())
        return KeyOptMap.from_item(KeyOptItem(ref, ctx))

    def visitSimple_stmt(self, ctx: ap.Simple_stmtContext | Any) -> KeyOptMap:
        if ctx.import_stmt() or ctx.dep_import_stmt():
            return super().visitChildren(ctx)
        return KeyOptMap.empty()

    @classmethod
    def survey(cls, file_path: Path, ctx: ParserRuleContext) -> Context:
        surveyor = cls()
        context = Context(file_path=file_path, scope_ctx=ctx, refs={})
        for ref, item in surveyor.visit(ctx):
            if ref in context.refs:
                raise errors.AtoKeyError.from_ctx(
                    ctx, f"Duplicate declaration of {ref}"
                )
            context.refs[ref] = item
        return context


class Lofty(AtopileParserVisitor, BasicsMixin, PhysicalValuesMixin, SequenceMixin):
    def __init__(self) -> None:
        super().__init__()
        self._scopes = FuncDict[ParserRuleContext, Context]()

    def visitDeclaration_stmt(self, ctx: ap.Declaration_stmtContext) -> KeyOptMap:
        """Handle declaration statements."""
        assigned_value_ref = self.visitName_or_attr(ctx.name_or_attr())
        if len(assigned_value_ref) > 1:
            raise errors.AtoSyntaxError.from_ctx(
                ctx, f"Can't declare fields in a nested object {assigned_value_ref}"
            )

        assigned_name = assigned_value_ref[0]

        # FIXME: how we can mark declarations w/ faebryk core?
        warnings.warn(f"Declaring {assigned_name} ignored")

        return KeyOptMap.empty()

    def _index_file(self, file_path: Path) -> Context:
        ast = parser.get_ast_from_file(file_path)
        if ast in self._scopes:
            return self._scopes[ast]

        context = Surveyor.survey(file_path, ast)
        self._scopes[ast] = context
        return context

    def _import_item(
        self, context: Context, item: Context.ImportPlaceholder
    ) -> Type[L.Node] | ap.BlockdefContext:
        from_path = Path(item.from_path)

        if from_path.suffix == ".py":
            with _sys_path_context(context.file_path.parent):
                module = importlib.import_module(from_path.stem)

            node = module
            for ref in item.ref:
                try:
                    node = getattr(node, ref)
                except AttributeError as ex:
                    raise errors.AtoKeyError.from_ctx(
                        item.original_ctx, f"No attribute '{ref}' found on {node}"
                    ) from ex
            return node

        elif from_path.suffix == ".ato":
            context = self._index_file(from_path)
            node = item
            for ref in item.ref:
                if ref not in context.refs:
                    raise errors.AtoKeyError.from_ctx(
                        item.original_ctx, f"No declaration of {ref} in {from_path}"
                    )
                node = context.refs[ref]
            return node

        else:
            raise errors.AtoImportNotFoundError.from_ctx(
                item.original_ctx, f"Can't import file type {from_path.suffix}"
            )

    def _get_referenced_item(
        self, context: Context, ref: Ref
    ) -> Type[L.Node] | ap.BlockdefContext | None:
        if ref not in context.refs:
            return None

        item = context.refs[ref]
        # Ensure the item is resolved, if not already
        if isinstance(item, Context.ImportPlaceholder):
            item = self._import_item(context, item)
            context.refs[ref] = item

        return item

    def _build_ato_node(self, ctx: ap.BlockdefContext) -> L.Node:
        # Find the superclass of the new node, if there's one defined
        supers_refs = [
            self.visitName_or_attr(super_ctx) for super_ctx in ctx.name_or_attr()
        ]
        if len(supers_refs) > 1:
            raise errors.AtoNotImplementedError.from_ctx(
                ctx, f"Can't declare blocks with multiple superclasses {supers_refs}"
            )

        # Create a base node to build off
        if supers_refs:
            base_node = self._init_node(ctx, ctx, supers_refs[0])
        else:
            # Create a shell of base-node to build off
            block_type = ctx.blocktype()
            assert isinstance(block_type, ap.BlocktypeContext)
            if block_type.INTERFACE():
                base_type = L.ModuleInterface
            elif block_type.COMPONENT() or block_type.MODULE():
                # TODO: distinguish between components and modules
                base_type = L.Module
            else:
                raise ValueError(f"Unknown block type {block_type.getText()}")
            base_node = base_type()

        # Make the noise
        for err_cltr, (ref, item) in errors.iter_through_errors(self.visitBlock(ctx.block())):
            with err_cltr():
                if ref in base_node:
                    raise errors.AtoKeyError.from_ctx(ctx, f"Duplicate declaration of {ref}")
                base_node[ref] = item

        return base_node

    def _init_node(
        self, stmt_ctx: ParserRuleContext, context: Context, ref: Ref
    ) -> L.Node:
        if item := self._get_referenced_item(context, ref):
            if isinstance(item, L.Node):
                return item()
            elif isinstance(item, ap.BlockdefContext):
                new_node = self._build_ato_node(item)
                new_node.add_trait(from_dsl(stmt_ctx))
                return new_node
            else:
                raise ValueError(f"Unknown item type {item}")
        else:
            raise errors.AtoKeyError.from_ctx(
                stmt_ctx, f"No class or block definition found for {ref}"
            )

    def visitAssign_stmt(self, ctx: ap.Assign_stmtContext) -> KeyOptMap:
        """Assignment values and create new instance of things."""
        assigned_ref = self.visitName_or_attr(ctx.name_or_attr())

        assigned_name: str = assigned_ref[-1]
        assignable_ctx = ctx.assignable()
        assert isinstance(assignable_ctx, ap.AssignableContext)

        ########## Handle New Statements ##########
        if new_stmt_ctx := assignable_ctx.new_stmt():
            if len(assigned_ref) > 1:
                raise errors.AtoSyntaxError.from_ctx(
                    ctx, f"Can't declare fields in a nested object {assigned_ref}"
                )

            assert isinstance(new_stmt_ctx, ap.New_stmtContext)
            ref = self.visitName_or_attr(new_stmt_ctx.name_or_attr())

            context = self._scopes[ctx]
            new_node = self._init_node(ctx, context, ref)
            return KeyOptMap.from_item(KeyOptItem.from_kv(assigned_ref, new_node))

        ########## Handle Reserved Assignments ##########
        # TODO: handle special assignments for reserved names in atopile

        ########## Handle Actual Assignments ##########
        # Figure out what Instance object the assignment is being made to
        # TODO: handle assignments. This is kinda hard before we need to actually
        # translate to faebryk core maths models
        # raise NotImplementedError
        warnings.warn(f"Assigning {assigned_name} ignored")
        return KeyOptMap.empty()

    def visitCum_assign_stmt(self, ctx: ap.Cum_assign_stmtContext | Any):
        """
        Cumulative assignments can only be made on top of
        nothing (implicitly declared) or declared, but undefined values.

        Unlike assignments, they may not implicitly declare an attribute.
        """
        raise NotImplementedError
        return KeyOptMap.empty()

    def visitSet_assign_stmt(self, ctx: ap.Set_assign_stmtContext):
        """
        Set cumulative assignments can only be made on top of
        nothing (implicitly declared) or declared, but undefined values.

        Unlike assignments, they may not implicitly declare an attribute.
        """
        raise NotImplementedError
        return KeyOptMap.empty()

    def visitPindef_stmt(self, ctx: ap.Pindef_stmtContext) -> KeyOptMap:
        """TODO:"""
        return self.visit_pin_or_signal_helper(ctx)

    def visitSignaldef_stmt(self, ctx: ap.Signaldef_stmtContext) -> KeyOptMap:
        """TODO:"""
        return self.visit_pin_or_signal_helper(ctx)

    def visitConnect_stmt(self, ctx: ap.Connect_stmtContext) -> KeyOptMap:
        """
        Connect interfaces together
        """
        raise NotImplementedError

        return KeyOptMap.empty()

    def visitConnectable(self, ctx: ap.ConnectableContext) -> Instance:
        """Return the address of the connectable object."""
        raise NotImplementedError
        return KeyOptMap.empty()

    def visitRetype_stmt(self, ctx: ap.Retype_stmtContext | Any) -> KeyOptMap:
        raise NotImplementedError
        return KeyOptMap.empty()

    def visitImport_stmt(self, ctx: ap.Import_stmtContext | Any) -> KeyOptMap:
        raise NotImplementedError
        return KeyOptMap.empty()

    def visitDep_import_stmt(self, ctx: ap.Dep_import_stmtContext | Any) -> KeyOptMap:
        raise NotImplementedError
        return KeyOptMap.empty()

    def visitAssert_stmt(self, ctx: ap.Assert_stmtContext) -> KeyOptMap:
        """Handle assertion statements."""
        raise NotImplementedError
        return KeyOptMap.empty()

    def visitArithmetic_expression(
        self, ctx: ap.Arithmetic_expressionContext
    ) -> KeyOptMap:
        """
        Handle arithmetic expressions, yielding either a numeric value or callable expression

        This sits here because we need to defer these to Roley,
        with the context of the current instance.
        """
        raise NotImplementedError
        return KeyOptMap.empty()


lofty = Lofty()
