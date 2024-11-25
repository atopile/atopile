"""
Build faebryk core objects from ato DSL.
"""

import importlib
import itertools
import logging
import operator
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from itertools import chain
from pathlib import Path
from typing import (
    Any,
    Callable,
    Iterable,
    Type,
)

from antlr4 import ParserRuleContext
from pint import UndefinedUnitError

import faebryk.core.parameter as fab_param
import faebryk.library._F as F
import faebryk.libs.library.L as L
from atopile import errors
from atopile.datatypes import KeyOptItem, KeyOptMap, Ref, StackList
from atopile.parse import parser
from atopile.parser.AtopileParser import AtopileParser as ap
from atopile.parser.AtopileParserVisitor import AtopileParserVisitor
from faebryk.core.node import NodeException
from faebryk.core.trait import Trait
from faebryk.libs.exceptions import FaebrykException
from faebryk.libs.picker.picker import DescriptiveProperties
from faebryk.libs.units import Quantity, Unit, UnitCompatibilityError, dimensionless
from faebryk.libs.util import FuncDict

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
    @staticmethod
    def _get_unit_from_ctx(ctx: ParserRuleContext) -> Unit:
        """Return a pint unit from a context."""
        unit_str = ctx.getText()
        try:
            return Unit(unit_str)
        except UndefinedUnitError as ex:
            raise errors.AtoUnknownUnitError.from_ctx(
                ctx, f"Unknown unit '{unit_str}'"
            ) from ex

    def visitLiteral_physical(self, ctx: ap.Literal_physicalContext) -> L.Range:
        """Yield a physical value from a physical context."""
        if ctx.quantity():
            qty = self.visitQuantity(ctx.quantity())
            value = L.Single(qty)
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

        return Quantity(value, unit)

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
            tol_qty = tol_num * self._get_unit_from_ctx(tol_name)
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
            for err_cltr, child in errors.iter_through_errors(children):
                with err_cltr():
                    child_result = self.visit(child)
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


class BlockNotFoundError(errors.AtoKeyError):
    """
    Raised when a block doesn't exist.
    """


@contextmanager
def _sys_path_context(path: Path):
    """Add a path to the system path for the duration of the context."""
    sys.path.append(path)
    try:
        yield
    finally:
        sys.path.remove(path)


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


class Surveyor(BasicsMixin, SequenceMixin, AtopileParserVisitor):
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
            raise errors.AtoError.from_ctx(from_dsl_.src_ctx, str(ex)) from ex
        else:
            raise ex
    except FaebrykException as ex:
        # TODO: consolidate faebryk exceptions
        raise ex


def has_attr_or_property(obj: object, attr: str) -> bool:
    return hasattr(obj, attr) or (
        hasattr(type(obj), attr) and isinstance(getattr(type(obj), attr), property)
    )


def try_set_attr(obj: object, attr: str, value: Any) -> bool:
    if hasattr(obj, attr) or (
        hasattr(type(obj), attr)
        and isinstance(getattr(type(obj), attr), property)
        and getattr(type(obj), attr).fset is not None
    ):
        setattr(obj, attr, value)
        return True
    else:
        return False


def _write_only_property(func: Callable):
    def raise_write_only(*args, **kwargs):
        raise AttributeError(f"{func.__name__} is write-only")

    return property(
        fget=raise_write_only,
        fset=func,
    )


class _has_kicad_footprint_name_defined(F.has_footprint_impl):
    """
    This trait defers footprint creation until it's needed,
    which means we can construct the underlying pin map
    """

    def __init__(self, lib_reference: str, pinmap: dict[str, F.Electrical]):
        super().__init__()
        self.lib_reference = lib_reference
        self.pinmap = pinmap

    def _try_get_footprint(self) -> F.Footprint | None:
        if fps := self.obj.get_children(direct_only=True, types=F.Footprint):
            return next(iter(fps))
        else:
            return None

    def get_footprint(self) -> F.Footprint:
        if fps := self._try_get_footprint():
            return fps
        else:
            fp = F.KicadFootprint(
                self.lib_reference,
                pin_names=list(self.pinmap.keys()),
            )
            self.get_trait(F.can_attach_to_footprint).attach(fp)
            self.set_footprint(fp)
            return fp

    def handle_duplicate(
        self, old: "_has_kicad_footprint_name_defined", node: fab_param.Node
    ) -> bool:
        if old._try_get_footprint():
            raise RuntimeError("Too late to set footprint")

        # Update the existing trait...
        old.lib_reference = self.lib_reference
        old.pinmap.update(self.pinmap)
        # ... and we don't need to attach the new
        return False


class AtoComponent(L.Module):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.pinmap = {}

    @L.rt_field
    def attach_to_footprint(self):
        return F.can_attach_to_footprint_via_pinmap(self.pinmap)

    @L.rt_field
    def has_designator_prefix(self):
        return F.has_designator_prefix_defined(F.has_designator_prefix.Prefix.U)

    def add_pin(self, name: str) -> F.Electrical:
        if _is_int(name):
            py_name = f"_{name}"
        else:
            py_name = name

        mif = self.add(F.Electrical(), name=py_name)
        self.pinmap[name] = mif
        return mif

    @_write_only_property
    def footprint(self, value: str):
        self.add(_has_kicad_footprint_name_defined(value, self.pinmap))

    @_write_only_property
    def lcsc_id(self, value: str):
        # handles duplicates gracefully
        self.add(F.has_descriptive_properties_defined({"LCSC": value}))

    @_write_only_property
    def manufacturer(self, value: str):
        # handles duplicates gracefully
        self.add(
            F.has_descriptive_properties_defined(
                {DescriptiveProperties.manufacturer: value}
            )
        )

    @_write_only_property
    def mpn(self, value: str):
        # handles duplicates gracefully
        self.add(
            F.has_descriptive_properties_defined({DescriptiveProperties.partno: value})
        )

    @_write_only_property
    def designator(self, value: str):
        self.add(F.has_designator_prefix_defined(value))


class ShimResistor(F.Resistor):
    """Temporary shim to translate `value` to `resistance`."""

    @property
    def value(self) -> L.Range:
        return self.resistance

    @value.setter
    def value(self, value: L.Range):
        self.resistance.alias_is(value)

    @_write_only_property
    def footprint(self, value: str):
        if value.startswith("R"):
            value = value[1:]
        self.package = value

    @_write_only_property
    def package(self, value: str):
        reqs = [(value, 2)]  # package, pin-count
        if fp_req := self.try_get_trait(F.has_footprint_requirement):
            fp_req.reqs = reqs
        else:
            self.add(F.has_footprint_requirement_defined(reqs))

    @_write_only_property
    def lcsc_id(self, value: str):
        # handles duplicates gracefully
        self.add(F.has_descriptive_properties_defined({"LCSC": value}))

    @_write_only_property
    def manufacturer(self, value: str):
        # handles duplicates gracefully
        self.add(
            F.has_descriptive_properties_defined(
                {DescriptiveProperties.manufacturer: value}
            )
        )

    @_write_only_property
    def mpn(self, value: str):
        # handles duplicates gracefully
        self.add(
            F.has_descriptive_properties_defined({DescriptiveProperties.partno: value})
        )


class ShimCapacitor(F.Capacitor):
    """Temporary shim to translate `value` to `capacitance`."""

    @property
    def value(self) -> L.Range:
        return self.capacitance

    @value.setter
    def value(self, value: L.Range):
        self.capacitance.alias_is(value)

    @_write_only_property
    def footprint(self, value: str):
        if value.startswith("C"):
            value = value[1:]
        self.package = value

    @_write_only_property
    def package(self, value: str):
        reqs = [(value, 2)]  # package, pin-count
        if fp_req := self.try_get_trait(F.has_footprint_requirement):
            fp_req.reqs = reqs
        else:
            self.add(F.has_footprint_requirement_defined(reqs))

    @_write_only_property
    def lcsc_id(self, value: str):
        # handles duplicates gracefully
        self.add(F.has_descriptive_properties_defined({"LCSC": value}))

    @_write_only_property
    def manufacturer(self, value: str):
        # handles duplicates gracefully
        self.add(
            F.has_descriptive_properties_defined(
                {DescriptiveProperties.manufacturer: value}
            )
        )

    @_write_only_property
    def mpn(self, value: str):
        # handles duplicates gracefully
        self.add(
            F.has_descriptive_properties_defined({DescriptiveProperties.partno: value})
        )


class Lofty(BasicsMixin, PhysicalValuesMixin, SequenceMixin, AtopileParserVisitor):
    def __init__(self) -> None:
        super().__init__()
        self._scopes = FuncDict[ParserRuleContext, Context]()
        self._node_stack = StackList[L.Node]()
        self._promised_params = FuncDict[L.Node, list[ParserRuleContext]]()
        self._param_assignments = FuncDict[
            fab_param.Parameter, tuple[L.Range | L.Single, ParserRuleContext | None]
        ]()

    def build_ast(
        self, ast: ap.File_inputContext, ref: Ref, file_path: Path | None = None
    ) -> L.Node:
        context = self._index_ast(ast, file_path)
        try:
            return self._build(context, ref)
        finally:
            self._finish()

    def build_file(self, path: Path, ref: Ref) -> L.Node:
        context = self._index_file(path)
        try:
            return self._build(context, ref)
        finally:
            self._finish()

    def _build(self, context: Context, ref: Ref) -> L.Node:
        if ref not in context.refs:
            raise errors.AtoKeyError.from_ctx(
                context.scope_ctx, f"No declaration of {ref} in {context.file_path}"
            )
        return self._init_node(context.scope_ctx, ref)

    def _finish(self):
        with errors.ExceptionAccumulator() as ex_acc:
            for param, (value, ctx) in self._param_assignments.items():
                with ex_acc.collect(), ato_error_converter():
                    if value is None:
                        raise errors.AtoKeyError.from_ctx(
                            ctx, f"Parameter {param} never assigned"
                        )

                    # Set final value of parameter
                    param.add(from_dsl(ctx))
                    try:
                        param.alias_is(value)
                    except UnitCompatibilityError as ex:
                        raise errors.AtoTypeError.from_ctx(ctx, str(ex)) from ex

            for param, ctxs in self._promised_params.items():
                for ctx in ctxs:
                    with ex_acc.collect():
                        raise errors.AtoKeyError.from_ctx(
                            ctx, f"Attribute {param} referenced, but never assigned"
                        )

    @property
    def _current_node(self) -> L.Node:
        return self._node_stack[-1]

    def _index_ast(
        self, ast: ap.File_inputContext, file_path: Path | None = None
    ) -> Context:
        if ast in self._scopes:
            return self._scopes[ast]

        context = Surveyor.survey(file_path, ast)
        self._scopes[ast] = context
        return context

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
        shim_map: dict[tuple[str, Ref], Type[L.Node]] = {
            ("generics/resistors.ato", Ref.from_one("Resistor")): ShimResistor,
            ("generics/capacitors.ato", Ref.from_one("Capacitor")): ShimCapacitor,
        }
        ref = (item.from_path, item.ref)
        if ref in shim_map:
            return shim_map[ref]

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
            # TODO: shimming integer names to make valid python identifiers
            if _is_int(name):
                name = f"_{name}"

            try:
                node = self.get_node_attr(node, name)
            except AttributeError as ex:
                # Wah wah wah - we don't know what this is
                raise errors.AtoKeyError.from_ctx(
                    ctx, f"{ref[:i]} has no attribute '{name}'"
                ) from ex
        return node

    def _try_get_referenced_node(
        self, ref: Ref, ctx: ParserRuleContext
    ) -> L.Node | None:
        try:
            return self._get_referenced_node(ref, ctx)
        except errors.AtoKeyError:
            return None

    def _build_ato_node(self, ctx: ap.BlockdefContext) -> L.Node:
        # Find the superclass of the new node, if there's one defined
        if super_ctx := ctx.name_or_attr():
            super_ref = self.visitName_or_attr(super_ctx)
            # Create a base node to build off
            base_node = self._init_node(ctx, super_ref)
        else:
            # Create a shell of base-node to build off
            block_type = ctx.blocktype()
            assert isinstance(block_type, ap.BlocktypeContext)
            if block_type.INTERFACE():
                base_node = L.ModuleInterface()
            elif block_type.COMPONENT():
                base_node = AtoComponent()
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
            if isinstance(item, type) and issubclass(item, L.Node):
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

    def _ensure_param(
        self,
        node: L.Node,
        name: str,
        src_ctx: ParserRuleContext,
    ) -> fab_param.Parameter:
        try:
            return self.get_node_attr(node, name)
        except AttributeError:
            default = fab_param.Parameter()
            param = node.add(default, name=name)
            self._promised_params.setdefault(param, []).append(src_ctx)
            return param

    @staticmethod
    def _attach_range_to_param(param: fab_param.Parameter, range: L.Range):
        param.alias_is(range)

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
            target = self._get_referenced_node(assigned_ref[:-1], ctx)
        else:
            target = self._current_node

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
                errors.AtoError.from_ctx(
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

        if not isinstance(self._current_node, AtoComponent):
            raise errors.AtoTypeError.from_ctx(
                ctx, f"Can't declare pins on components of type {self._current_node}"
            )

        mif = self._current_node.add_pin(name)
        return KeyOptMap.from_item(KeyOptItem.from_kv(name, mif))

    def visitSignaldef_stmt(self, ctx: ap.Signaldef_stmtContext) -> KeyOptMap:
        name = self.visitName(ctx.name())
        mif = self._current_node.add(F.Electrical(), name=name)
        return KeyOptMap.from_item(KeyOptItem.from_kv(name, mif))

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
        elif numerical_ctx := ctx.numerical_pin_ref():
            pin_name = numerical_ctx.getText()
            return self.get_node_attr(self._current_node, pin_name)
        else:
            raise ValueError(f"Unhandled connectable type {ctx}")

    def visitRetype_stmt(self, ctx: ap.Retype_stmtContext) -> KeyOptMap:
        from_, to = map(self.visitName_or_attr, ctx.name_or_attr())
        node = self._get_referenced_node(from_, ctx)
        if not isinstance(node, L.Module):
            raise errors.AtoTypeError.from_ctx(ctx, f"Can't retype {node}")

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
    ) -> fab_param.ParameterOperatable:
        if ctx.OR_OP() or ctx.AND_OP():
            lh = self.visitArithmetic_expression(ctx.arithmetic_expression())
            rh = self.visitSum(ctx.sum_())

            if ctx.OR_OP():
                return operator.or_(lh, rh)
            else:
                return operator.and_(lh, rh)

        return self.visitSum(ctx.sum_())

    def visitSum(self, ctx: ap.SumContext) -> fab_param.ParameterOperatable:
        if ctx.ADD() or ctx.MINUS():
            lh = self.visitSum(ctx.sum_())
            rh = self.visitTerm(ctx.term())

            if ctx.ADD():
                return operator.add(lh, rh)
            else:
                return operator.sub(lh, rh)

        return self.visitTerm(ctx.term())

    def visitTerm(self, ctx: ap.TermContext) -> fab_param.ParameterOperatable:
        if ctx.STAR() or ctx.DIV():
            lh = self.visitTerm(ctx.term())
            rh = self.visitPower(ctx.power())

            if ctx.STAR():
                return operator.mul(lh, rh)
            else:
                return operator.truediv(lh, rh)

        return self.visitPower(ctx.power())

    def visitPower(self, ctx: ap.PowerContext) -> fab_param.ParameterOperatable:
        if ctx.POWER():
            base = self.visitFunctional(ctx.functional())
            exp = self.visitFunctional(ctx.functional())
            return operator.pow(base, exp)
        else:
            return self.visitFunctional(ctx.functional(0))

    def visitFunctional(
        self, ctx: ap.FunctionalContext
    ) -> fab_param.ParameterOperatable:
        if ctx.name():
            # TODO: implement min/max
            raise NotImplementedError
        else:
            return self.visitBound(ctx.bound(0))

    def visitBound(self, ctx: ap.BoundContext) -> fab_param.ParameterOperatable:
        return self.visitAtom(ctx.atom())

    def visitAtom(self, ctx: ap.AtomContext) -> fab_param.ParameterOperatable:
        if ctx.name_or_attr():
            ref = self.visitName_or_attr(ctx.name_or_attr())
            if len(ref) > 1:
                target = self._get_referenced_node(ref[:-1], ctx)
            else:
                target = self._current_node
            return self._ensure_param(target, ref[-1], ctx)

        elif ctx.literal_physical():
            return self.visitLiteral_physical(ctx.literal_physical())

        elif group_ctx := ctx.arithmetic_group():
            assert isinstance(group_ctx, ap.Arithmetic_groupContext)
            return self.visitArithmetic_expression(group_ctx.arithmetic_expression())

        raise ValueError(f"Unhandled atom type {ctx}")

    def visitLiteral_physical(self, ctx: ap.Literal_physicalContext) -> L.Range:
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
            raise errors.AtoSyntaxError.from_ctx(
                ctx, f"Can't declare fields in a nested object {assigned_value_ref}"
            )

        assigned_name = assigned_value_ref[0]

        if assigned_name in self._param_assignments:
            errors.AtoKeyError.from_ctx(
                ctx,
                f"Ignoring declaration of {assigned_name} because it's already defined",
            ).log(to_level=logging.WARNING)

        else:
            # TODO: greedily create this param?
            # param = self._ensure_param(self._current_node, assigned_name, None, ctx)
            self._param_assignments[assigned_name] = (None, ctx)

        return KeyOptMap.empty()

    def visitPass_stmt(self, ctx: ap.Pass_stmtContext) -> KeyOptMap:
        return KeyOptMap.empty()


lofty = Lofty()
