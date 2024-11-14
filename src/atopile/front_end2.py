"""
Build faebryk core objects from ato DSL.

TODO:
- [ ] Handle units
- [ ] Implement a __deepcopy__ method for the Node class to slowly re-walking the AST
"""

import collections
import importlib
import itertools
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
import faebryk.core.parameter as fab_param

from atopile import address, config, errors, parse_utils
from atopile.datatypes import KeyOptItem, KeyOptMap, StackList
from atopile.front_end import _get_unit_from_ctx
from atopile.parse import parser
from atopile.parse_utils import get_src_info_from_ctx
from atopile.parser.AtopileParser import AtopileParser as ap
from atopile.parser.AtopileParserVisitor import AtopileParserVisitor
from faebryk.libs.units import Quantity, dimensionless

from atopile.datatypes import Ref

log = logging.getLogger(__name__)


class from_dsl(Trait.decless()):
    def __init__(self, src_ctx: ParserRuleContext) -> None:
        super().__init__()
        self.src_ctx = src_ctx


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
    def visitLiteral_physical(self, ctx: ap.Literal_physicalContext) -> L.Range:
        """Yield a physical value from a physical context."""
        if ctx.quantity():
            qty = self.visitQuantity(ctx.quantity())
            value = L.Range(qty, qty)
        elif ctx.bilateral_quantity():
            value = self.visitBilateral_quantity(ctx.bilateral_quantity())
        elif ctx.bound_quantity():
            value = self.visitBound_quantity(ctx.bound_quantity())
        else:
            raise ValueError  # this should be protected because it shouldn't be parseable
        return value

    def visitQuantity(self, ctx: ap.QuantityContext) -> Quantity:
        """Yield a physical value from an implicit quantity context."""
        raw: str = ctx.NUMBER().getText()
        if raw.startswith("0x"):
            value = int(raw, 16)
        else:
            value = float(raw)

        # Ignore the positive unary operator
        if ctx.MINUS():
            value = -value

        if unit_ctx := ctx.name():
            unit = _get_unit_from_ctx(unit_ctx)
            return value * unit
        else:
            return value * dimensionless

    def visitBilateral_quantity(self, ctx: ap.Bilateral_quantityContext) -> L.Range:
        """Yield a physical value from a bilateral quantity context."""
        nominal_qty = self.visitQuantity(ctx.quantity())

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
            if nominal_qty == 0:
                raise errors.AtoError.from_ctx(
                    tol_ctx,
                    "Can't calculate tolerance percentage of a nominal value of zero",
                )

            # Calculate tolerance value from percentage/ppm
            tol_value = tol_num / tol_divider
            return L.Range.from_center_rel(nominal_qty, tol_value)

        # Ensure the tolerance has a unit
        if tol_name := tol_ctx.name():
            # In this case there's a named unit on the tolerance itself
            tol_qty = tol_num * _get_unit_from_ctx(tol_name)
        elif nominal_qty.unitless:
            tol_qty = tol_num * dimensionless
        else:
            tol_qty = tol_num * nominal_qty.units

        # Ensure units on the nominal quantity
        if nominal_qty.unitless:
            nominal_qty = nominal_qty * tol_qty.units

        # If the nominal has a unit, then we rely on the ranged value's unit compatibility
        if not nominal_qty.is_compatible_with(tol_qty):
            raise errors.AtoTypeError.from_ctx(
                tol_name,
                f"Tolerance unit '{tol_qty.units}' is not dimensionally"
                f" compatible with nominal unit '{nominal_qty.units}'",
            )

        return L.Range.from_center(nominal_qty, tol_qty)

    def visitBound_quantity(self, ctx: ap.Bound_quantityContext) -> L.Range:
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
            raise errors.AtoTypeError.from_ctx(
                ctx,
                f"Tolerance unit '{end.units}' is not dimensionally"
                f" compatible with nominal unit '{start.units}'",
            )

        return L.Range(start, end)


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


class _AtoComponent(L.Module):
    @L.rt_field
    def attach_to_footprint(self):
        return F.can_attach_to_footprint_via_pinmap({})

    def add_pin(self, name: str) -> F.Electrical:
        mif = self.add(F.Electrical(), name=name)
        self.get_trait(F.can_attach_to_footprint_via_pinmap).pinmap[name] = mif
        return mif


class Lofty(AtopileParserVisitor, BasicsMixin, PhysicalValuesMixin, SequenceMixin):
    def __init__(self) -> None:
        super().__init__()
        self._scopes = FuncDict[ParserRuleContext, Context]()
        self._node_stack = StackList[L.Node]()

    @property
    def _current_node(self) -> L.Node:
        return self._node_stack[-1]

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

    def _get_referenced_class(
        self, ctx: ParserRuleContext, ref: Ref
    ) -> Type[L.Node] | ap.BlockdefContext | None:
        while ctx not in self._scopes:
            if ctx.parentCtx is None:
                raise ValueError(f"No scope found for {ref}")
            ctx = ctx.parentCtx

        context = self._scopes[ctx]

        # TODO: there are more cases to check here,
        # eg. if we have part of a ref resolved
        if ref not in context.refs:
            return None

        item = context.refs[ref]
        # Ensure the item is resolved, if not already
        if isinstance(item, Context.ImportPlaceholder):
            item = self._import_item(context, item)
            context.refs[ref] = item

        return item

    def _get_referenced_node(self, ref: Ref, ctx: ParserRuleContext) -> L.Node:
        node = self._current_node
        for i, name in enumerate(ref):

            # FIXME: shimming integer names to make valid python identifiers
            try:
                int(name)
            except ValueError:
                pass
            else:
                name = f"_{name}"

            if hasattr(node, name):
                node = getattr(node, name)
            else:
                raise errors.AtoKeyError.from_ctx(
                    ctx, f"{ref[:i]} has no attribute '{name}'"
                )
        return node

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
            base_node = self._init_node(ctx, supers_refs[0])
        else:
            # Create a shell of base-node to build off
            block_type = ctx.blocktype()
            assert isinstance(block_type, ap.BlocktypeContext)
            if block_type.INTERFACE():
                base_node = L.ModuleInterface()
            elif block_type.COMPONENT():
                base_node = _AtoComponent()
            elif block_type.MODULE():
                base_node = L.Module()
            else:
                raise ValueError(f"Unknown block type {block_type.getText()}")

        # Make the noise
        with self._node_stack.enter(base_node):
            self.visitBlock(ctx.block())

        return base_node

    def _init_node(self, stmt_ctx: ParserRuleContext, ref: Ref) -> L.Node:
        if item := self._get_referenced_class(stmt_ctx, ref):
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

            new_node = self._init_node(ctx, ref)
            self._current_node.add(new_node, name=assigned_name)

        target = self._get_referenced_node(assigned_ref, ctx)

        ########## Handle Reserved Assignments ##########
        # TODO: handle special assignments for reserved names in atopile
        # TODO: shim "value" property, rated_xyz etc...
        # TODO: shim mpn / LCSC id etc...

        ########## Handle Actual Assignments ##########
        if literal_physical_ctx := assignable_ctx.literal_physical():
            value = self.visitLiteral_physical(literal_physical_ctx)
            param = fab_param.Parameter(soft_set=value)
            target.add(param, name=assigned_name)
        elif arithmetic_expression_ctx := assignable_ctx.arithmetic_expression():
            expr = self.visitArithmetic_expression(arithmetic_expression_ctx)
            param = fab_param.Parameter()
            param.alias_is(expr)
            target.add(param, name=assigned_name)
        elif assignable_ctx.string() or assignable_ctx.boolean_():
            warnings.warn(f"Assigning {assigned_name} ignored")
        else:
            raise ValueError(f"Unhandled assignable type {assignable_ctx}")

        return KeyOptMap.empty()

    def visitPindef_stmt(self, ctx: ap.Pindef_stmtContext) -> KeyOptMap:
        # TODO: something useful with the pin mapping
        if ctx.name():
            name = self.visitName_or_attr(ctx.name())
        elif ctx.totally_an_integer():
            name = f"_{ctx.totally_an_integer().getText()}"
        elif ctx.string():
            name = self.visitString(ctx.string())
        else:
            raise ValueError(f"Unhandled pin name type {ctx}")

        if not isinstance(self._current_node, _AtoComponent):
            raise errors.AtoTypeError.from_ctx(
                ctx, f"Can't declare pins on components of type {self._current_node}"
            )

        mif = self._current_node.add_pin(name)
        return KeyOptMap.from_item(KeyOptItem(name, mif))

    def visitSignaldef_stmt(self, ctx: ap.Signaldef_stmtContext) -> KeyOptMap:
        name = self.visitName_or_attr(ctx.name())
        mif = self._current_node.add(F.Electrical(), name=name)
        return KeyOptMap.from_item(KeyOptItem(name, mif))

    def visitConnect_stmt(self, ctx: ap.Connect_stmtContext) -> KeyOptMap:
        """Connect interfaces together"""
        connectables = [self.visitConnectable(c) for c in ctx.connectable()]
        for err_cltr, (a, b) in errors.iter_through_errors(
            itertools.pairwise(connectables)
        ):
            with err_cltr():
                a.connect(b)
        return KeyOptMap.empty()

    def visitConnectable(self, ctx: ap.ConnectableContext) -> L.ModuleInterface:
        """Return the address of the connectable object."""
        if def_stmt := ctx.pindef_stmt() or ctx.signaldef_stmt():
            (_, mif), *_ = self.visit(def_stmt)
            return mif
        elif name_or_attr_ctx := ctx.name_or_attr():
            ref = self.visitName_or_attr(name_or_attr_ctx)
            return self._get_referenced_node(ref, ctx)

    def visitRetype_stmt(self, ctx: ap.Retype_stmtContext) -> KeyOptMap:
        from_, to = map(self.visitName_or_attr, ctx.name_or_attr())
        node = self._get_referenced_node(from_, ctx)
        if not isinstance(node, L.Module):
            raise errors.AtoTypeError.from_ctx(
                ctx, f"Can't retype {node}"
            )

        node.specialize(self._init_node(ctx, to))
        return KeyOptMap.empty()

    def visitBlockdef(self, ctx: ap.BlockdefContext):
        """Do nothing. Handled in Surveyor."""
        return KeyOptMap.empty()

    def visitImport_stmt(self, ctx: ap.Import_stmtContext) -> KeyOptMap:
        """Do nothing. Handled in Surveyor."""
        return KeyOptMap.empty()

    def visitDep_import_stmt(self, ctx: ap.Dep_import_stmtContext) -> KeyOptMap:
        """Do nothing. Handled in Surveyor."""
        return KeyOptMap.empty()

    def visitAssert_stmt(self, ctx: ap.Assert_stmtContext) -> KeyOptMap:
        comparisons = [c for _, c in self.visitComparison(ctx.comparison())]
        for cmp in comparisons:
            assert isinstance(cmp, fab_param.Constrainable)
            cmp.constrain()
        return KeyOptMap.empty()

    def visitComparison(self, ctx: ap.ComparisonContext) -> KeyOptMap:
        _visited = FuncDict[ParserRuleContext, fab_param.Parameter]()
        def _visit(ctx: ParserRuleContext) -> fab_param.Parameter:
            if ctx in _visited:
                return _visited[ctx]
            param = self.visit(ctx)
            _visited[ctx] = param
            return param

        params = []
        for lh_ctx, rh_ctx in itertools.pairwise(itertools.chain([ctx.arithmetic_expression()], ctx.compare_op_pair())):
            lh = _visit(lh_ctx.arithmetic_expression())
            rh = _visit(rh_ctx.arithmetic_expression())

            # HACK: this is a cheap way to get the operator string
            operator_str: str = rh_ctx.getChild(0).getText()
            match operator_str:
                case "<":
                    param = lh.operation_is_lt(rh)
                case ">":
                    param = lh.operation_is_gt(rh)
                case "<=":
                    param = lh.operation_is_le(rh)
                case ">=":
                    param = lh.operation_is_ge(rh)
                case "within":
                    param = lh.operation_is_subset(rh)
                case _:
                    # We shouldn't be able to get here with parseable input
                    raise ValueError(f"Unhandled operator {operator_str}")

            # TODO: should we be reducing here to a series of ANDs?
            params.append(param)

        return KeyOptMap([KeyOptItem.from_kv(None, p) for p in params])


    def visitLiteral_physical(self, ctx: ap.Literal_physicalContext) -> fab_param.Parameter:
        range_ = PhysicalValuesMixin.visitLiteral_physical(self, ctx)
        return fab_param.Parameter(soft_set=range_)

    def visitArithmetic_expression(
        self, ctx: ap.Arithmetic_expressionContext
    ) -> fab_param.Parameter:
        if ctx.OR_OP() or ctx.AND_OP():
            lh = self.visitArithmetic_expression(ctx.arithmetic_expression())
            rh = self.visitSum(ctx.sum_())

            if ctx.OR_OP():
                return lh.operation_or(rh)
            else:
                return lh.operation_and(rh)

        return self.visitSum(ctx.sum_())

    def visitSum(self, ctx: ap.SumContext) -> fab_param.Parameter:
        if ctx.ADD() or ctx.MINUS():
            lh = self.visitSum(ctx.sum_())
            rh = self.visitTerm(ctx.term())

            if ctx.ADD():
                return lh.operation_add(rh)
            else:
                return lh.operation_subtract(rh)

        return self.visitTerm(ctx.term())

    def visitTerm(self, ctx: ap.TermContext) -> fab_param.Parameter:
        if ctx.STAR() or ctx.DIV():
            lh = self.visitTerm(ctx.term())
            rh = self.visitPower(ctx.power())

            if ctx.STAR():
                return lh.operation_multiply(rh)
            else:
                return lh.operation_divide(rh)

        return self.visitPower(ctx.power())

    def visitPower(self, ctx: ap.PowerContext) -> fab_param.Parameter:
        if ctx.POWER():
            base = self.visitFunctional(ctx.functional())
            exp = self.visitFunctional(ctx.functional())
            return base.operation_power(exp)

        return self.visitFunctional(ctx.functional())

    def visitFunctional(self, ctx: ap.FunctionalContext) -> fab_param.Parameter:
        if ctx.name():
            raise NotImplementedError

        return self.visitBound(ctx.bound())

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

lofty = Lofty()
