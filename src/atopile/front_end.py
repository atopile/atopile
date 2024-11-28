"""
Build faebryk core objects from ato DSL.
"""

import itertools
import logging
import operator
import os
from contextlib import contextmanager
from dataclasses import dataclass
from itertools import chain
from pathlib import Path
from typing import (
    Any,
    Iterable,
    Type,
    cast,
)

from antlr4 import ParserRuleContext
from pint import UndefinedUnitError

import faebryk.core.parameter as fab_param
import faebryk.library._F as F
import faebryk.libs.library.L as L
from atopile import address, config, errors
from atopile._shim import Component, shim_map
from atopile.datatypes import KeyOptItem, KeyOptMap, Ref, StackList
from atopile.parse import parser
from atopile.parser.AtopileParser import AtopileParser as ap
from atopile.parser.AtopileParserVisitor import AtopileParserVisitor
from faebryk.core.node import NodeException
from faebryk.core.trait import Trait
from faebryk.libs.exceptions import (
    ExceptionAccumulator,
    downgrade,
    iter_through_errors,
)
from faebryk.libs.units import P, Quantity, Unit
from faebryk.libs.util import (
    FuncDict,
    has_attr_or_property,
    import_from_path,
    try_set_attr,
)

# Helpers for auto-upgrading on merge of the https://github.com/atopile/atopile/pull/522
try:
    from faebryk.libs.units import UnitCompatibilityError, dimensionless  # type: ignore
except ImportError:

    class UnitCompatibilityError(Exception):
        """Placeholder Exception"""

    dimensionless = P.dimensionless

try:
    from faebryk.libs.library.L import Range  # type: ignore
except ImportError:
    from faebryk.library._F import Range  # type: ignore

try:
    from faebryk.library import Single  # type: ignore
except ImportError:
    from faebryk.library._F import Constant as Single  # type: ignore


def _alias_is(lh, rh):
    try:
        return lh.alias_is(rh)
    except AttributeError:
        return lh.merge(rh)


# End helpers ---------------------------------------------------------------

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

    def visitAttr(self, ctx: ap.AttrContext) -> Ref:
        return Ref([self.visitName(name) for name in ctx.name()])

    def visitName_or_attr(self, ctx: ap.Name_or_attrContext) -> Ref:
        if ctx.name():
            return Ref.from_one(self.visitName(ctx.name()))
        elif ctx.attr():
            return self.visitAttr(ctx.attr())

        raise errors.UserException.from_ctx(ctx, "Expected a name or attribute")

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


class PhysicalValuesMixin:
    @staticmethod
    def _get_unit_from_ctx(ctx: ParserRuleContext) -> Unit:
        """Return a pint unit from a context."""
        unit_str = ctx.getText()
        try:
            return Unit(unit_str)
        except UndefinedUnitError as ex:
            raise errors.UserUnknownUnitError.from_ctx(
                ctx, f"Unknown unit '{unit_str}'"
            ) from ex

    def visitLiteral_physical(self, ctx: ap.Literal_physicalContext) -> Range:
        """Yield a physical value from a physical context."""
        if ctx.quantity():
            qty = self.visitQuantity(ctx.quantity())
            value = Single(qty)
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
            unit = self._get_unit_from_ctx(unit_ctx)
        else:
            unit = dimensionless

        return Quantity(value, unit)  # type: ignore

    def visitBilateral_quantity(self, ctx: ap.Bilateral_quantityContext) -> Range:
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
                raise errors.UserException.from_ctx(
                    tol_ctx,
                    "Can't calculate tolerance percentage of a nominal value of zero",
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

        assert isinstance(tol_qty, Quantity)

        # Ensure units on the nominal quantity
        if nominal_qty.unitless:
            nominal_qty = nominal_qty * tol_qty.units

        # If the nominal has a unit, then we rely on the ranged value's unit compatibility
        if not nominal_qty.is_compatible_with(tol_qty):
            raise errors.UserTypeError.from_ctx(
                tol_name,
                f"Tolerance unit '{tol_qty.units}' is not dimensionally"
                f" compatible with nominal unit '{nominal_qty.units}'",
            )

        return Range.from_center(nominal_qty, tol_qty)

    def visitBound_quantity(self, ctx: ap.Bound_quantityContext) -> Range:
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
                f"Tolerance unit '{end.units}' is not dimensionally"
                f" compatible with nominal unit '{start.units}'",
            )

        return Range(start, end)


class NOTHING:
    """A sentinel object to represent a "nothing" return value."""


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
            for err_cltr, child in iter_through_errors(children):
                with err_cltr():
                    # Since we're in a SequenceMixin, we need to cast self to the visitor type
                    child_result = cast(AtopileParserVisitor, self).visit(child)
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
        ref: Ref
        from_path: str
        original_ctx: ParserRuleContext

    # Location information re. the source of this module
    file_path: Path | None

    # Scope information
    scope_ctx: ap.BlockdefContext | ap.File_inputContext
    refs: dict[Ref, Type[L.Node] | ap.BlockdefContext | ImportPlaceholder]


class Wendy(BasicsMixin, SequenceMixin, AtopileParserVisitor):
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

    def visitImport_stmt(
        self, ctx: ap.Import_stmtContext
    ) -> KeyOptMap[Context.ImportPlaceholder]:
        lazy_imports = [
            Context.ImportPlaceholder(
                ref=self.visitName_or_attr(name_or_attr),
                from_path=self.visitString(ctx.string()),
                original_ctx=ctx,
            )
            for name_or_attr in ctx.name_or_attr()
        ]
        return KeyOptMap(KeyOptItem.from_kv(li.ref, li) for li in lazy_imports)

    def visitDep_import_stmt(
        self, ctx: ap.Dep_import_stmtContext
    ) -> KeyOptMap[Context.ImportPlaceholder]:
        lazy_import = Context.ImportPlaceholder(
            ref=self.visitName_or_attr(ctx.name_or_attr()),
            from_path=self.visitString(ctx.string()),
            original_ctx=ctx,
        )
        return KeyOptMap.from_kv(lazy_import.ref, lazy_import)

    def visitBlockdef(self, ctx: ap.BlockdefContext) -> KeyOptMap:
        ref = Ref.from_one(self.visitName(ctx.name()))
        return KeyOptMap.from_kv(ref, ctx)

    def visitSimple_stmt(self, ctx: ap.Simple_stmtContext | Any) -> KeyOptMap:
        if ctx.import_stmt() or ctx.dep_import_stmt():
            return super().visitChildren(ctx)
        return KeyOptMap.empty()

    @classmethod
    def survey(
        cls, file_path: Path | None, ctx: ap.BlockdefContext | ap.File_inputContext
    ) -> Context:
        surveyor = cls()
        context = Context(file_path=file_path, scope_ctx=ctx, refs={})
        for ref, item in surveyor.visit(ctx):
            if ref in context.refs:
                raise errors.UserKeyError.from_ctx(
                    ctx, f"Duplicate declaration of {ref}"
                )
            context.refs[ref] = item
        return context


def _is_int(name: str) -> bool:
    try:
        int(name)
    except ValueError:
        return False
    return True


@contextmanager
def ato_error_converter():
    try:
        yield
    except NodeException as ex:
        if from_dsl_ := ex.node.try_get_trait(from_dsl):
            raise errors.UserException.from_ctx(from_dsl_.src_ctx, str(ex)) from ex
        else:
            raise ex


class DeprecationError(errors.UserException):
    """
    Raised when a deprecated feature is used.
    """


class Bob(BasicsMixin, PhysicalValuesMixin, SequenceMixin, AtopileParserVisitor):
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
        self._scopes = FuncDict[ParserRuleContext, Context]()  # type: ignore
        self._python_classes = FuncDict[ap.BlockdefContext, Type[Component]]()  # type: ignore
        self._node_stack = StackList[L.Node]()  # type: ignore
        self._promised_params = FuncDict[L.Node, list[ParserRuleContext]]()  # type: ignore
        self._param_assignments = FuncDict[
            fab_param.Parameter, "tuple[Range | Single, ParserRuleContext | None]"  # type: ignore
        ]()

    def build_ast(
        self, ast: ap.File_inputContext, ref: Ref, file_path: Path | None = None
    ) -> L.Node:
        """Build a Module from an AST and reference."""
        file_path = self._sanitise_path(file_path) if file_path else None
        context = self._index_ast(ast, file_path)
        try:
            return self._build(context, ref)
        finally:
            self._finish()

    def build_file(self, path: Path, ref: Ref) -> L.Node:
        """Build a Module from a file and reference."""
        context = self._index_file(self._sanitise_path(path))
        try:
            return self._build(context, ref)
        finally:
            self._finish()

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
                self._scopes[ctx_].file_path, ".".join(ref)
            )

        return {
            addr: cls
            for ctx, cls in self._python_classes.items()
            if (addr := _get_addr(ctx)) is not None
        }

    def _build(self, context: Context, ref: Ref) -> L.Node:
        if ref not in context.refs:
            raise errors.UserKeyError.from_ctx(
                context.scope_ctx, f'No declaration of "{ref}" in {context.file_path}'
            )
        return self._init_node(context.scope_ctx, ref)

    def _finish(self):
        with ExceptionAccumulator() as ex_acc:
            for param, (value, ctx) in self._param_assignments.items():
                with ex_acc.collect(), ato_error_converter():
                    if value is None:
                        raise errors.UserKeyError.from_ctx(
                            ctx, f"Parameter {param} never assigned"
                        )

                    # Set final value of parameter
                    assert isinstance(
                        ctx, ParserRuleContext
                    )  # Since value and ctx should be None together
                    param.add(from_dsl(ctx))
                    try:
                        _alias_is(param, value)
                    except UnitCompatibilityError as ex:
                        raise errors.UserTypeError.from_ctx(ctx, str(ex)) from ex

            for param, ctxs in self._promised_params.items():
                for ctx in ctxs:
                    with ex_acc.collect():
                        raise errors.UserKeyError.from_ctx(
                            ctx, f"Attribute {param} referenced, but never assigned"
                        )

    @property
    def _current_node(self) -> L.Node:
        return self._node_stack[-1]

    @staticmethod
    def _sanitise_path(path: os.PathLike) -> Path:
        return Path(path).expanduser().resolve().absolute()

    def _index_ast(
        self, ast: ap.File_inputContext, file_path: Path | None = None
    ) -> Context:
        if ast in self._scopes:
            return self._scopes[ast]

        context = Wendy.survey(file_path, ast)
        self._scopes[ast] = context
        return context

    def _index_file(self, file_path: Path) -> Context:
        ast = parser.get_ast_from_file(file_path)
        return self._index_ast(ast, file_path)

    def _import_item(
        self, context: Context, item: Context.ImportPlaceholder
    ) -> Type[L.Node] | ap.BlockdefContext:
        # Build up search paths to check for the import in
        prj_context = config.get_project_context()
        search_paths = [
            prj_context.src_path,
            prj_context.module_path,
        ]
        if context.file_path is not None:
            search_paths.insert(0, context.file_path.parent)

        # Iterate though them, checking if any contains the thing we're looking for
        for search_path in search_paths:
            candidate_from_path = search_path / item.from_path
            if candidate_from_path.exists():
                break
        else:
            raise errors.UserFileNotFoundError.from_ctx(
                item.original_ctx,
                f"Can't find {item.from_path} in {", ".join(map(str, search_paths))}",
            )

        from_path = self._sanitise_path(candidate_from_path)

        # TODO: @v0.4: remove this shimming
        import_addr = address.AddrStr.from_parts(from_path, ".".join(item.ref))
        for shim_addr, (shim_cls, preferred) in shim_map.items():
            if import_addr.endswith(shim_addr):
                with downgrade(DeprecationError):
                    raise DeprecationError.from_ctx(
                        item.original_ctx,
                        f"Deprecated: {import_addr} is deprecated and a likeness"
                        f" is being shimmed in place for you. Use {preferred} instead.",
                    )
                return shim_cls

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
                        item.original_ctx, f"No attribute '{ref}' found on {node}"
                    ) from ex

            assert isinstance(node, type) and issubclass(node, L.Node)
            return node

        elif from_path.suffix == ".ato":
            context = self._index_file(from_path)
            if item.ref not in context.refs:
                raise errors.UserKeyError.from_ctx(
                    item.original_ctx, f"No declaration of {ref} in {from_path}"
                )
            node = context.refs[item.ref]

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
        self, ctx: ParserRuleContext, ref: Ref
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
                raise ValueError(f"Can't get class {ref} from {ctx}")

        # Ascend the tree until we find a scope that has the ref within it
        ctx_ = ctx
        while ctx_ not in self._scopes:
            if ctx_.parentCtx is None:
                raise ValueError(f"No scope found for {ref}")
            ctx_ = ctx_.parentCtx

        context = self._scopes[ctx_]

        # FIXME: there are more cases to check here,
        # eg. if we have part of a ref resolved
        if ref not in context.refs:
            raise errors.UserKeyError.from_ctx(
                ctx, f"No class or block definition found for {ref}"
            )

        item = context.refs[ref]
        # Ensure the item is resolved, if not already
        if isinstance(item, Context.ImportPlaceholder):
            # TODO: search path for these imports
            item = self._import_item(context, item)
            context.refs[ref] = item

        return item

    @staticmethod
    def get_node_attr(node: L.Node, name: str) -> L.Node:
        if _is_int(name):
            name = f"_{name}"

        if has_attr_or_property(node, name):
            # Build-time attributes are attached as real attributes
            return getattr(node, name)
        elif name in node.runtime:
            # Runtime attributes are attached as runtime attributes
            return node.runtime[name]
        else:
            # Wah wah wah - we don't know what this is
            raise AttributeError(name=name, obj=node)

    def _get_referenced_node(self, ref: Ref, ctx: ParserRuleContext) -> L.Node:
        node = self._current_node
        for i, name in enumerate(ref):
            # Shim integer names to make valid python identifiers
            if _is_int(name):
                name = f"_{name}"

            try:
                node = self.get_node_attr(node, name)
            except AttributeError as ex:
                # Wah wah wah - we don't know what this is
                raise errors.UserKeyError.from_ctx(
                    ctx, f"{ref[:i]} has no attribute '{name}'"
                ) from ex
        return node

    def _try_get_referenced_node(
        self, ref: Ref, ctx: ParserRuleContext
    ) -> L.Node | None:
        try:
            return self._get_referenced_node(ref, ctx)
        except errors.UserKeyError:
            return None

    def _new_node(
        self,
        item: ap.BlockdefContext | Type[L.Node],
        promised_supers: list[ap.BlockdefContext] | None = None,
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
        if promised_supers is None:
            promised_supers = []

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
            return super_class(), promised_supers

        if isinstance(item, ap.BlockdefContext):
            # Find the superclass of the new node, if there's one defined
            if super_ctx := item.name_or_attr():
                super_ref = self.visitName_or_attr(super_ctx)
                # Create a base node to build off
                base_class = self._get_referenced_class(item, super_ref)

            else:
                # Create a shell of base-node to build off
                block_type = item.blocktype()
                assert isinstance(block_type, ap.BlocktypeContext)
                if block_type.INTERFACE():
                    base_class = L.ModuleInterface
                elif block_type.COMPONENT():
                    base_class = Component
                elif block_type.MODULE():
                    base_class = L.Module
                else:
                    raise ValueError(f"Unknown block type {block_type.getText()}")

            # Descend into building the superclass. We've got no information
            # on when the super-chain will be resolved, so we need to promise
            # that this current blockdef will be visited as part of the init
            return self._new_node(base_class, [item] + promised_supers)

        # This should never happen
        raise ValueError(f"Unknown item type {item}")

    def _init_node(self, stmt_ctx: ParserRuleContext, ref: Ref) -> L.Node:
        """Kind of analogous to __init__ in Python, except that it's a factory"""
        new_node, promised_supers = self._new_node(
            self._get_referenced_class(stmt_ctx, ref)
        )

        with self._node_stack.enter(new_node):
            for super_ctx in promised_supers:
                self.visitBlock(super_ctx.block())

        new_node.add_trait(from_dsl(stmt_ctx))
        return new_node

    def _ensure_param(
        self,
        node: L.Node,
        name: str,
        src_ctx: ParserRuleContext,
    ) -> fab_param.Parameter:
        """
        Get a param from a node. If it doesn't exist, create it and promise to assign
        it later. Used in forward-declaration.
        """
        try:
            node = self.get_node_attr(node, name)
            assert isinstance(node, fab_param.Parameter)
            return node
        except AttributeError:
            default = fab_param.Parameter()
            param = node.add(default, name=name)
            self._promised_params.setdefault(param, []).append(src_ctx)
            return param

    def _fufill_param_promise(self, param: fab_param.Parameter):
        if param in self._promised_params:
            del self._promised_params[param]

    def visitAssign_stmt(self, ctx: ap.Assign_stmtContext) -> KeyOptMap:
        """Assignment values and create new instance of things."""
        assigned_ref = self.visitName_or_attr(ctx.name_or_attr())

        assigned_name: str = assigned_ref[-1]
        assignable_ctx = ctx.assignable()
        assert isinstance(assignable_ctx, ap.AssignableContext)

        if len(assigned_ref) > 1:
            target = self._get_referenced_node(Ref(assigned_ref[:-1]), ctx)
        else:
            target = self._current_node

        ########## Handle New Statements ##########
        if new_stmt_ctx := assignable_ctx.new_stmt():
            if len(assigned_ref) > 1:
                raise errors.UserSyntaxError.from_ctx(
                    ctx, f"Can't declare fields in a nested object {assigned_ref}"
                )

            assert isinstance(new_stmt_ctx, ap.New_stmtContext)
            ref = self.visitName_or_attr(new_stmt_ctx.name_or_attr())

            new_node = self._init_node(ctx, ref)
            self._current_node.add(new_node, name=assigned_name)
            return KeyOptMap.empty()

        ########## Handle Regular Assignments ##########
        value = self.visit(assignable_ctx)
        if assignable_ctx.literal_physical() or assignable_ctx.arithmetic_expression():
            param = self._ensure_param(target, assigned_name, ctx)
            self._param_assignments[param] = (value, ctx)
            self._fufill_param_promise(param)

        elif assignable_ctx.string() or assignable_ctx.boolean_():
            # Check if it's a property or attribute that can be set
            if not try_set_attr(target, assigned_name, value):
                errors.UserException.from_ctx(
                    ctx,
                    f"Ignoring assignment of {value} to {assigned_name} on {target}",
                ).log(to_level=logging.WARNING)

        else:
            raise ValueError(f"Unhandled assignable type {assignable_ctx.getText()}")

        return KeyOptMap.empty()

    def visitPindef_stmt(self, ctx: ap.Pindef_stmtContext) -> KeyOptMap:
        if ctx.name():
            name = self.visitName(ctx.name())
        elif ctx.totally_an_integer():
            name = f"{ctx.totally_an_integer().getText()}"
        elif ctx.string():
            name = self.visitString(ctx.string())
        else:
            raise ValueError(f"Unhandled pin name type {ctx}")

        if not isinstance(self._current_node, Component):
            raise errors.UserTypeError.from_ctx(
                ctx, f"Can't declare pins on components of type {self._current_node}"
            )

        mif = self._current_node.add_pin(name)
        return KeyOptMap.from_item(KeyOptItem.from_kv(Ref.from_one(name), mif))

    def visitSignaldef_stmt(self, ctx: ap.Signaldef_stmtContext) -> KeyOptMap:
        name = self.visitName(ctx.name())
        # TODO: @v0.4: remove this protection
        if (
            has_attr_or_property(self._current_node, name)
            or name in self._current_node.runtime
        ):
            with downgrade(DeprecationError):
                raise DeprecationError(
                    f"Signal {name} already exists, skipping."
                    " In the future this will be an error."
                )
            mif = self.get_node_attr(self._current_node, name)
        else:
            mif = self._current_node.add(F.Electrical(), name=name)

        return KeyOptMap.from_item(KeyOptItem.from_kv(Ref.from_one(name), mif))

    @classmethod
    def _connect(cls, a: L.ModuleInterface, b: L.ModuleInterface, nested: bool = False):
        """
        FIXME: In ato, we allowed duck-typing of connectables
        We need to reconcile this with the strong typing
        in faebryk's connect method
        For now, we'll attempt to connect by name, and log a deprecation
        warning if that succeeds, else, re-raise the exception emitted
        by the connect method
        """
        try:
            a.connect(b)
        except NodeException as top_ex:
            for name, (c_a, c_b) in a.zip_children_by_name_with(
                b, L.ModuleInterface
            ).items():
                if c_a is None:
                    if has_attr_or_property(a, name):
                        c_a = getattr(a, name)
                    else:
                        raise

                if c_b is None:
                    if has_attr_or_property(b, name):
                        c_b = getattr(b, name)
                    else:
                        raise

                try:
                    cls._connect(c_a, c_b, nested=True)
                except NodeException:
                    raise top_ex

            else:
                if not nested:
                    logging.warning(
                        f"Deprecated: Connected {a} to {b} by duck-typing."
                        " They should be of the same type."
                    )

    def visitConnect_stmt(self, ctx: ap.Connect_stmtContext) -> KeyOptMap:
        """Connect interfaces together"""
        connectables = [self.visitConnectable(c) for c in ctx.connectable()]
        for err_cltr, (a, b) in iter_through_errors(itertools.pairwise(connectables)):
            with err_cltr():
                self._connect(a, b)

        return KeyOptMap.empty()

    def visitConnectable(self, ctx: ap.ConnectableContext) -> L.ModuleInterface:
        """Return the address of the connectable object."""
        if def_stmt := ctx.pindef_stmt() or ctx.signaldef_stmt():
            (_, mif), *_ = self.visit(def_stmt)
            return mif
        elif name_or_attr_ctx := ctx.name_or_attr():
            ref = self.visitName_or_attr(name_or_attr_ctx)
            node = self._get_referenced_node(ref, ctx)
            assert isinstance(node, L.ModuleInterface)
            return node
        elif numerical_ctx := ctx.numerical_pin_ref():
            pin_name = numerical_ctx.getText()
            node = self.get_node_attr(self._current_node, pin_name)
            assert isinstance(node, L.ModuleInterface)
            return node
        else:
            raise ValueError(f"Unhandled connectable type {ctx}")

    def visitRetype_stmt(self, ctx: ap.Retype_stmtContext) -> KeyOptMap:
        from_, to = map(self.visitName_or_attr, ctx.name_or_attr())
        node = self._get_referenced_node(from_, ctx)
        if not isinstance(node, L.Module):
            raise errors.UserTypeError.from_ctx(ctx, f"Can't retype {node}")

        narrow = self._init_node(ctx, to)
        assert isinstance(narrow, L.Module)
        node.specialize(narrow)
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
            assert isinstance(cmp, fab_param.ConstrainableExpression)
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
        for lh_ctx, rh_ctx in itertools.pairwise(
            itertools.chain([ctx.arithmetic_expression()], ctx.compare_op_pair())
        ):
            lh = _visit(lh_ctx.arithmetic_expression())
            rh = _visit(rh_ctx.arithmetic_expression())

            # HACK: this is a cheap way to get the operator string
            operator_str: str = rh_ctx.getChild(0).getText()
            match operator_str:
                case "<":
                    op = operator.lt
                case ">":
                    op = operator.gt
                case "<=":
                    op = operator.le
                case ">=":
                    op = operator.ge
                case "within":
                    op = operator.contains
                case _:
                    # We shouldn't be able to get here with parseable input
                    raise ValueError(f"Unhandled operator {operator_str}")

            # TODO: should we be reducing here to a series of ANDs?
            params.append(op(lh, rh))

        return KeyOptMap([KeyOptItem.from_kv(None, p) for p in params])

    def visitArithmetic_expression(
        self, ctx: ap.Arithmetic_expressionContext
    ) -> "fab_param.ParameterOperatable":
        if ctx.OR_OP() or ctx.AND_OP():
            lh = self.visitArithmetic_expression(ctx.arithmetic_expression())
            rh = self.visitSum(ctx.sum_())

            if ctx.OR_OP():
                return operator.or_(lh, rh)
            else:
                return operator.and_(lh, rh)

        return self.visitSum(ctx.sum_())

    def visitSum(self, ctx: ap.SumContext) -> "fab_param.ParameterOperatable":
        if ctx.ADD() or ctx.MINUS():
            lh = self.visitSum(ctx.sum_())
            rh = self.visitTerm(ctx.term())

            if ctx.ADD():
                return operator.add(lh, rh)
            else:
                return operator.sub(lh, rh)

        return self.visitTerm(ctx.term())

    def visitTerm(self, ctx: ap.TermContext) -> "fab_param.ParameterOperatable":
        if ctx.STAR() or ctx.DIV():
            lh = self.visitTerm(ctx.term())
            rh = self.visitPower(ctx.power())

            if ctx.STAR():
                return operator.mul(lh, rh)
            else:
                return operator.truediv(lh, rh)

        return self.visitPower(ctx.power())

    def visitPower(self, ctx: ap.PowerContext) -> "fab_param.ParameterOperatable":
        if ctx.POWER():
            base = self.visitFunctional(ctx.functional())
            exp = self.visitFunctional(ctx.functional())
            return operator.pow(base, exp)
        else:
            return self.visitFunctional(ctx.functional(0))

    def visitFunctional(
        self, ctx: ap.FunctionalContext
    ) -> "fab_param.ParameterOperatable":
        if ctx.name():
            # TODO: implement min/max
            raise NotImplementedError
        else:
            return self.visitBound(ctx.bound(0))

    def visitBound(self, ctx: ap.BoundContext) -> "fab_param.ParameterOperatable":
        return self.visitAtom(ctx.atom())

    def visitAtom(self, ctx: ap.AtomContext) -> "fab_param.ParameterOperatable":
        if ctx.name_or_attr():
            ref = self.visitName_or_attr(ctx.name_or_attr())
            if len(ref) > 1:
                target = self._get_referenced_node(Ref(ref[:-1]), ctx)
            else:
                target = self._current_node
            return self._ensure_param(target, ref[-1], ctx)

        elif ctx.literal_physical():
            return self.visitLiteral_physical(ctx.literal_physical())

        elif group_ctx := ctx.arithmetic_group():
            assert isinstance(group_ctx, ap.Arithmetic_groupContext)
            return self.visitArithmetic_expression(group_ctx.arithmetic_expression())

        raise ValueError(f"Unhandled atom type {ctx}")

    def visitLiteral_physical(self, ctx: ap.Literal_physicalContext) -> Range:
        return PhysicalValuesMixin.visitLiteral_physical(self, ctx)

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
            raise errors.UserSyntaxError.from_ctx(
                ctx, f"Can't declare fields in a nested object {assigned_value_ref}"
            )

        assigned_name = assigned_value_ref[0]

        param = self._ensure_param(self._current_node, assigned_name, ctx)
        if param not in self._param_assignments:
            self._param_assignments[param] = (None, ctx)
        else:
            errors.UserKeyError.from_ctx(
                ctx,
                f"Ignoring declaration of {assigned_name} because it's already defined",
            ).log(to_level=logging.WARNING)

        return KeyOptMap.empty()

    def visitPass_stmt(self, ctx: ap.Pass_stmtContext) -> KeyOptMap:
        return KeyOptMap.empty()


bob = Bob()
