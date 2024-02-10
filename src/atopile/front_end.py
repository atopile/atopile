"""
This datamodel represents the code in a clean, simple and traversable way,
but doesn't resolve names of things.
In building this datamodel, we check for name collisions, but we don't resolve them yet.
"""
import enum
from collections import ChainMap
from contextlib import ExitStack, contextmanager
from itertools import chain
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Optional

import pint
from antlr4 import ParserRuleContext
from attrs import define, field, resolve_types

from atopile import address, errors
from atopile.address import AddrStr
from atopile.datatypes import KeyOptItem, KeyOptMap, Ref
from atopile.generic_methods import recurse
from atopile.parse import parser
from atopile.parse_utils import get_src_info_from_ctx
from atopile.parser.AtopileParser import AtopileParser
from atopile.parser.AtopileParser import AtopileParser as ap
from atopile.parser.AtopileParserVisitor import AtopileParserVisitor


@define
class Base:
    """Represent a base class for all things."""

    src_ctx: Optional[ParserRuleContext] = field(kw_only=True, default=None)


@define
class Import(Base):
    """Represent an import statement."""

    obj_addr: AddrStr

    def __repr__(self) -> str:
        return f"<Import {self.obj_addr}>"


@define
class Replacement(Base):
    """Represent a replacement statement."""

    new_super_ref: Ref


@define(repr=False)
class ObjectDef(Base):
    """
    Represent the definition or skeleton of an object
    so we know where we can go to find the object later
    without actually building the whole file.

    This is mainly because we don't want to hit errors that
    aren't relevant to the current build - instead leaving them
    to be hit in the case we're actually building that object.
    """

    super_ref: Optional[Ref]
    imports: Mapping[Ref, Import]

    local_defs: Mapping[Ref, "ObjectDef"]
    replacements: Mapping[Ref, Replacement]

    # attached immediately to the object post construction
    closure: Optional[tuple["ObjectDef"]] = None  # in order of lookup
    address: Optional[AddrStr] = None

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.address}>"


@define
class Physical(Base):
    """Let's get physical!"""
    unit: pint.Unit
    min_val: float
    max_val: float

    def __str__(self) -> str:
        return f"{self.nominal} +/- {self.tolerance} {self.unit}"

    @property
    def nominal(self) -> float:
        return (self.min_val + self.max_val) / 2

    @property
    def tolerance(self) -> float:
        return (self.max_val - self.min_val) / 2

    @property
    def tolerance_pct(self) -> Optional[float]:
        if self.nominal == 0:
            return None
        return self.tolerance / self.nominal * 100

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.min_val} to {self.max_val} {self.unit}>"

    def to_dict(self) -> dict:
        """Convert the Physical instance to a dictionary."""
        data = {
            "unit": str(self.unit),
            "min_val": self.min_val,
            "max_val": self.max_val,
            "nominal": self.nominal,
            "tolerance": self.tolerance,
            "tolerance_pct": self.tolerance_pct,
        }
        return data


@define(repr=False)
class ObjectLayer(Base):
    """
    Represent a layer in the object hierarchy.
    This holds all the values assigned to the object.
    """

    # information about where this object is found in multiple forms
    # this is redundant with one another (eg. you can compute one from the other)
    # but it's useful to have all of them for different purposes
    obj_def: ObjectDef

    # None indicates that this is a root object
    super: Optional["ObjectLayer"]

    # the local objects and vars are things we navigate to a lot
    # objs: Optional[Mapping[str, "Object"]] = None
    data: Optional[Mapping[str, Any]] = None

    # data from the lock-file entry associated with this object
    # lock_data: Mapping[str, Any] = {}  # TODO: this should point to a lockfile entry

    @property
    def address(self) -> AddrStr:
        return self.obj_def.address

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.obj_def.address}>"


resolve_types(ObjectLayer)


## The below datastructures are created from the above datamodel as a second stage


@define
class Link(Base):
    """Represent a connection between two connectable things."""

    # TODO: we may not need this using loop-soup
    # the reason this currently exists is to allow us to map joints between instances
    # these make sense only in the context of the pins and signals, which aren't
    # language fundamentals as much as net objects - eg. they're useful only from
    # a specific electrical perspective
    # origin_link: Link

    parent: "Instance"
    source: "Instance"
    target: "Instance"

    def __repr__(self) -> str:
        return f"<Link {repr(self.source)} -> {repr(self.target)}>"


@define
class Instance(Base):
    """
    Represents the specific instance, capturing, the story you told of
    how to get there in it's mapping stacks.
    """

    # origin information
    # much of this information is redundant, however it's all highly referenced
    # so it's useful to have it all at hand
    addr: AddrStr
    supers: list["ObjectLayer"] = field(factory=list)
    children: dict[str, "Instance"] = field(factory=dict)
    links: list[Link] = field(factory=list)

    data: Optional[
        Mapping[str, Any]
    ] = None  # this is a chainmap inheriting from the supers as well

    override_data: dict[str, Any] = field(factory=dict)
    _override_location: dict[str, ObjectLayer] = field(factory=dict)

    # TODO: for later
    # lock_data: Optional[Mapping[str, Any]] = None

    # attached immediately after construction
    parents: Optional[tuple["Instance"]] = None

    def __repr__(self) -> str:
        return f"<Instance {self.addr}>"


resolve_types(Instance)
resolve_types(Link)


class _Sentinel(enum.Enum):
    NOTHING = enum.auto()


NOTHING = _Sentinel.NOTHING


def make_obj_layer(
    address: AddrStr, super: Optional[ObjectLayer] = None
) -> ObjectLayer:
    """Create a new object layer from an address and a set of supers."""
    obj_def = ObjectDef(
        address=address,
        super_ref=Ref.empty(),
        imports={},
        local_defs={},
        replacements={},
    )
    return ObjectLayer(
        obj_def=obj_def,
        super=super,
        data={},
    )


MODULE: ObjectLayer = make_obj_layer(AddrStr("<Built-in>:Module"))
COMPONENT: ObjectLayer = make_obj_layer(AddrStr("<Built-in>:Component"), super=MODULE)
PIN: ObjectLayer = make_obj_layer(AddrStr("<Built-in>:Pin"))
SIGNAL: ObjectLayer = make_obj_layer(AddrStr("<Built-in>:Signal"))
INTERFACE: ObjectLayer = make_obj_layer(AddrStr("<Built-in>:Interface"))


BUILTINS_BY_REF = {
    Ref.from_one("MODULE"): MODULE,
    Ref.from_one("COMPONENT"): COMPONENT,
    Ref.from_one("INTERFACE"): INTERFACE,
    Ref.from_one("PIN"): PIN,
    Ref.from_one("SIGNAL"): SIGNAL,
}


BUILTINS_BY_ADDR = {
    MODULE.address: MODULE,
    COMPONENT.address: COMPONENT,
    PIN.address: PIN,
    SIGNAL.address: SIGNAL,
    INTERFACE.address: INTERFACE,
}


def _get_unit_from_ctx(ctx: ParserRuleContext) -> pint.Unit:
    """Return a pint unit from a context."""
    unit_str = ctx.getText()
    try:
        return pint.Unit(unit_str)
    except pint.UndefinedUnitError as ex:
        raise errors.AtoUnknownUnitError.from_ctx(
            ctx, f"Unknown unit '{unit_str}'"
        ) from ex


class BaseTranslator(AtopileParserVisitor):
    """
    Dizzy is responsible for mixing cement, sand, aggregate, and water to create concrete.
    Ref.: https://www.youtube.com/watch?v=drBge9JyloA
    """

    def __init__(
        self,
    ) -> None:
        super().__init__()

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

        def __visit() -> KeyOptMap:
            for err_cltr, child in errors.iter_through_errors(children):
                with err_cltr():
                    child_result = self.visit(child)
                    if child_result is not NOTHING:
                        yield child_result

        child_results = chain.from_iterable(__visit())
        child_results = list(item for item in child_results if item is not NOTHING)
        child_results = KeyOptMap(KeyOptItem(cr) for cr in child_results)

        return KeyOptMap(child_results)

    def visit_ref_helper(
        self,
        ctx: ap.NameContext
        | ap.AttrContext
        | ap.Name_or_attrContext
        | ap.Totally_an_integerContext,
    ) -> Ref:
        """
        Visit any referencey thing and ensure it's returned as a reference
        """
        if isinstance(
            ctx,
            (
                ap.NameContext,
                ap.Totally_an_integerContext,
            ),
        ):
            return Ref.from_one(str(self.visit(ctx)))
        if isinstance(ctx, ap.Numerical_pin_refContext):
            name_part = self.visit_ref_helper(ctx.name_or_attr())
            return name_part.add_name(str(self.visit(ctx)))
        if isinstance(ctx, (ap.AttrContext, ap.Name_or_attrContext)):
            return Ref(
                map(str, self.visit(ctx)),
            )
        raise errors.AtoError(f"Unknown reference type: {type(ctx)}")

    def visitName(self, ctx: ap.NameContext) -> str:
        """
        If this is an int, convert it to one (for pins), else return the name as a string.
        """
        return ctx.getText()

    def visitAttr(self, ctx: ap.AttrContext) -> Ref:
        return Ref(self.visitName(name) for name in ctx.name())

    def visitName_or_attr(self, ctx: ap.Name_or_attrContext) -> Ref:
        if ctx.name():
            name = self.visitName(ctx.name())
            return Ref.from_one(name)
        elif ctx.attr():
            return self.visitAttr(ctx.attr())

        raise errors.AtoError("Expected a name or attribute")

    def visitString(self, ctx: ap.StringContext) -> str:
        return ctx.getText().strip("\"'")

    def visitBoolean_(self, ctx: ap.Boolean_Context) -> bool:
        return ctx.getText().lower() == "true"

    def visitSimple_stmt(
        self, ctx: ap.Simple_stmtContext
    ) -> Iterable[_Sentinel | KeyOptItem]:
        """
        This is practically here as a development shim to assert the result is as intended
        """
        result = self.visitChildren(ctx)
        for item in result:
            if item is not NOTHING:
                assert isinstance(item, KeyOptItem)
        return result

    def visitStmt(self, ctx: ap.StmtContext) -> KeyOptMap:
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

    def visitBlock(self, ctx) -> KeyOptMap:
        if ctx.stmt():
            return self.visit_iterable_helper(ctx.stmt())
        if ctx.simple_stmts():
            return self.visitSimple_stmts(ctx.simple_stmts())
        raise ValueError  # this should be protected because it shouldn't be parseable

    def visitImplicit_quantity(self, ctx: AtopileParser.Implicit_quantityContext) -> Physical:
        """Yield a physical value from an implicit quantity context."""
        value = float(ctx.NUMBER().getText())

        if ctx.name():
            unit = _get_unit_from_ctx(ctx.name())
        else:
            unit = pint.Unit("")

        return Physical(
            src_ctx=ctx,
            min_val=value,
            max_val=value,
            unit=unit,
        )

    def visitBilateral_quantity(self, ctx: AtopileParser.Bilateral_quantityContext) -> Physical:
        """Yield a physical value from a bilateral quantity context."""
        nominal = float(ctx.bilateral_nominal().NUMBER().getText())

        if ctx.bilateral_nominal().name():
            unit = _get_unit_from_ctx(ctx.bilateral_nominal().name())
        else:
            unit = pint.Unit("")

        tol_ctx: AtopileParser.Bilateral_toleranceContext = ctx.bilateral_tolerance()
        tol_num = float(tol_ctx.NUMBER().getText())

        if tol_ctx.PERCENT():
            tol_divider = 100
        # FIXME: hardcoding this seems wrong, but the parser/lexer wasn't picking up on it
        elif tol_ctx.name() and tol_ctx.name().getText() == "ppm":
            tol_divider = 1E6
        else:
            tol_divider = None

        if tol_divider:
            if nominal == 0:
                raise errors.AtoError.from_ctx(
                    tol_ctx,
                    "Can't calculate tolerance percentage of a nominal value of zero",
                )

            # In this case, life's a little easier, and we can simply multiply the nominal
            return Physical(
                src_ctx=ctx,
                min_val=nominal * (1 - tol_num / tol_divider),
                max_val=nominal * (1 + tol_num / tol_divider),
                unit=unit,
            )

        if tol_ctx.name():
            # In this case there's a named unit on the tolerance itself
            # We need to make sure it's dimensionally compatible with the nominal
            tolerance_unit = _get_unit_from_ctx(tol_ctx.name())
            try:
                tolerance = (tol_num * tolerance_unit).to(unit).magnitude
            except pint.DimensionalityError as ex:
                raise errors.AtoTypeError.from_ctx(
                    tol_ctx.name(),
                    f"Tolerance unit '{tolerance_unit}' is not dimensionally"
                    f" compatible with nominal unit '{unit}'",
                ) from ex

            return Physical(
                src_ctx=ctx,
                min_val=nominal - tolerance,
                max_val=nominal + tolerance,
                unit=unit,
            )

        # If there's no unit or percent, then we have a simple tolerance in the same units
        # as the nominal
        return Physical(
            src_ctx=ctx,
            min_val=nominal - tol_num,
            max_val=nominal + tol_num,
            unit=unit,
        )

    def visitBound_quantity(self, ctx: AtopileParser.Bound_quantityContext) -> Physical:
        """Yield a physical value from a bound quantity context."""
        def _parse_end(ctx: AtopileParser.Quantity_endContext) -> tuple[float, Optional[pint.Unit]]:
            value = float(ctx.NUMBER().getText())
            if ctx.name():
                unit = _get_unit_from_ctx(ctx.name())
            else:
                unit = None
            return value, unit

        start_val, start_unit = _parse_end(ctx.quantity_end(0))
        end_val, end_unit = _parse_end(ctx.quantity_end(1))

        if start_unit is None and end_unit is None:
            unit = pint.Unit("")
        elif start_unit and end_unit:
            unit = start_unit
            try:
                end_val = (end_val * end_unit).to(start_unit).magnitude
            except pint.DimensionalityError as ex:
                raise errors.AtoTypeError.from_ctx(
                    ctx,
                    f"Tolerance unit '{end_unit}' is not dimensionally"
                    f" compatible with nominal unit '{start_unit}'",
                ) from ex
        elif start_unit:
            unit = start_unit
        else:
            unit = end_unit

        return Physical(
            src_ctx=ctx,
            min_val=start_val,
            max_val=end_val,
            unit=unit,
        )

    def visitPhysical(self, ctx: AtopileParser.PhysicalContext) -> Physical:
        """Yield a physical value from a physical context."""
        if ctx.implicit_quantity():
            return self.visitImplicit_quantity(ctx.implicit_quantity())
        if ctx.bilateral_quantity():
            return self.visitBilateral_quantity(ctx.bilateral_quantity())
        if ctx.bound_quantity():
            return self.visitBound_quantity(ctx.bound_quantity())

        raise ValueError  # this should be protected because it shouldn't be parseable

    def visitAssignable(self, ctx: ap.AssignableContext) -> Physical | str | bool:
        """Yield something we can place in a set of locals."""
        if ctx.physical():
            return self.visitPhysical(ctx.physical())

        if ctx.string():
            return self.visitString(ctx)

        assert (
            not ctx.new_stmt()
        ), "New statements should have already been filtered out."
        raise TypeError(f"Unexpected assignable type {type(ctx)}")

    def visitTotally_an_integer(self, ctx: ap.Totally_an_integerContext) -> int:
        text = ctx.getText()
        try:
            return int(text)
        except ValueError:
            raise errors.AtoTypeError.from_ctx(  # pylint: disable=raise-missing-from
                ctx, f"Expected an integer, but got {text}"
            )


class Scoop(BaseTranslator):
    """Scoop's job is to map out all the object definitions in the code."""

    def __init__(
        self,
        ast_getter: Callable[[str | Path], ParserRuleContext],
        search_paths: Iterable[Path | str],
    ) -> None:
        self.ast_getter = ast_getter
        self.search_paths = search_paths
        self._output_cache: dict[AddrStr, ObjectDef] = {}
        super().__init__()

    def get_obj_def(self, addr: AddrStr) -> ObjectDef:
        """Returns the ObjectDef for a given address."""
        if addr not in self._output_cache:
            file = address.get_file(addr)
            file_ast = self.ast_getter(file)
            obj = self.visitFile_input(file_ast)
            assert isinstance(obj, ObjectDef)
            # this operation puts it and it's children in the cache
            self._register_obj_tree(obj, AddrStr(file), ())
        try:
            return self._output_cache[addr]
        except KeyError as ex:
            raise BlockNotFoundError(f"No block named $addr in {address.get_file(addr)}", addr=addr) from ex

    def _register_obj_tree(
        self, obj: ObjectDef, addr: AddrStr, closure: tuple[ObjectDef]
    ) -> None:
        """Register address info to the object, and add it to the cache."""
        obj.address = addr
        obj.closure = closure
        child_closure = (obj,) + closure
        self._output_cache[addr] = obj
        for ref, child in obj.local_defs.items():
            assert len(ref) == 1
            assert isinstance(ref[0], str)
            child_addr = address.add_entry(addr, ref[0])
            self._register_obj_tree(child, child_addr, child_closure)

    def visitFile_input(self, ctx: ap.File_inputContext) -> ObjectDef:
        """Visit a file input and return it's object."""
        locals_ = self.visit_iterable_helper(ctx.stmt())

        # FIXME: clean this up, and do much better name collision detection on it
        local_defs = {}
        imports = {}
        for ref, local in locals_:
            if isinstance(local, ObjectDef):
                local_defs[ref] = local
            elif isinstance(local, Import):
                assert ref is not None
                imports[ref] = local
            else:
                raise errors.AtoError(f"Unexpected local type: {type(local)}")

        file_obj = ObjectDef(
            src_ctx=ctx,
            super_ref=Ref.from_one("MODULE"),
            imports=imports,
            local_defs=local_defs,
            replacements={},
        )

        return file_obj

    def visitBlockdef(self, ctx: ap.BlockdefContext) -> KeyOptItem[ObjectDef]:
        """Visit a blockdef and return it's object."""
        if ctx.FROM():
            if not ctx.name_or_attr():
                raise errors.AtoSyntaxError("Expected a name or attribute after 'from'")
            block_super_ref = self.visit_ref_helper(ctx.name_or_attr())
        else:
            block_super_ref = self.visitBlocktype(ctx.blocktype())

        locals_ = self.visitBlock(ctx.block())

        # FIXME: this needs far better name collision detection
        local_defs = {}
        imports = {}
        replacements = {}
        for ref, local in locals_:
            if isinstance(local, ObjectDef):
                local_defs[ref] = local
            elif isinstance(local, Import):
                imports[ref] = local
            elif isinstance(local, Replacement):
                replacements[ref] = local
            else:
                raise errors.AtoError(f"Unexpected local type: {type(local)}")

        block_obj = ObjectDef(
            src_ctx=ctx,
            super_ref=block_super_ref,
            imports=imports,
            local_defs=local_defs,
            replacements=replacements,
        )

        block_name = self.visit_ref_helper(ctx.name())

        return KeyOptItem.from_kv(block_name, block_obj)

    def visitImport_stmt(self, ctx: ap.Import_stmtContext) -> KeyOptMap:
        from_file: str = self.visitString(ctx.string())
        import_what_ref = self.visit_ref_helper(ctx.name_or_attr())

        _errors = []

        if not from_file:
            _errors.append(
                errors.AtoError("Expected a 'from <file-path>' after 'import'")
            )
        if not import_what_ref:
            _errors.append(
                errors.AtoError("Expected a name or attribute to import after 'import'")
            )

        if import_what_ref == "*":
            # import everything
            raise NotImplementedError("import *")

        # get the current working directory
        current_file, _, _ = get_src_info_from_ctx(ctx)
        current_file = Path(current_file)
        if current_file.is_file():
            search_paths = chain((current_file.parent,), self.search_paths)
        else:
            search_paths = self.search_paths

        for search_path in search_paths:
            candidate_path: Path = (search_path / from_file).resolve().absolute()
            if candidate_path.exists():
                break
        else:
            raise errors.AtoImportNotFoundError.from_ctx(  # pylint: disable=raise-missing-from
                ctx, f"File '{from_file}' not found."
            )

        import_addr = address.add_entries(str(candidate_path), import_what_ref)

        import_ = Import(
            src_ctx=ctx,
            obj_addr=import_addr,
        )

        return KeyOptMap.from_kv(import_what_ref, import_)

    def visitBlocktype(self, ctx: ap.BlocktypeContext) -> Ref:
        """Return the address of a block type."""
        block_type_name = ctx.getText()
        match block_type_name:
            case "module":
                return Ref.from_one("MODULE")
            case "component":
                return Ref.from_one("COMPONENT")
            case "interface":
                return Ref.from_one("INTERFACE")
            case _:
                raise errors.AtoError(f"Unknown block type '{block_type_name}'")

    def visitRetype_stmt(self, ctx: ap.Retype_stmtContext) -> KeyOptMap:
        """TODO:"""
        # TODO: we should check the validity of the replacement here

        to_replace = self.visit_ref_helper(ctx.name_or_attr(0))
        new_class = self.visit_ref_helper(ctx.name_or_attr(1))

        replacement = Replacement(
            src_ctx=ctx,
            new_super_ref=new_class,
        )

        return KeyOptMap.from_kv(to_replace, replacement)

    def visitSimple_stmt(
        self, ctx: ap.Simple_stmtContext
    ) -> Iterable[_Sentinel | KeyOptItem]:
        """We have to be selective here to deal with the ignored children properly."""
        if ctx.retype_stmt() or ctx.import_stmt():
            return super().visitSimple_stmt(ctx)

        return KeyOptMap.empty()


def lookup_obj_in_closure(context: ObjectDef, ref: Ref) -> AddrStr:
    """
    This method finds an object in the closure of another object, traversing import statements.
    """
    assert context.closure is not None
    for scope in context.closure:
        obj_lead = scope.local_defs.get(ref[:1])
        import_leads = {
            imp_ref: imp
            for imp_ref, imp in scope.imports.items()
            if ref[0] == imp_ref[0]
        }

        if import_leads and obj_lead:
            # TODO: improve error message with details about what items are conflicting
            raise errors.AtoAmbiguousReferenceError.from_ctx(
                scope.src_ctx, f"Name '{ref[0]}' is ambiguous in '{scope}'."
            )

        if obj_lead is not None:
            if len(ref) > 1:
                raise NotImplementedError
            return obj_lead.address

        if ref in scope.imports:
            return scope.imports[ref].obj_addr

    if ref in BUILTINS_BY_REF:
        return BUILTINS_BY_REF[ref].address

    raise errors.AtoKeyError.from_ctx(
        context.src_ctx, f"Couldn't find {ref} in the scope of {context}"
    )


class BlockNotFoundError(errors.AtoKeyError):
    """
    Raised when a block doesn't exist.
    """


class Dizzy(BaseTranslator):
    """Dizzy's job is to create object layers."""

    def __init__(
        self,
        obj_def_getter: Callable[[AddrStr], ObjectDef],
    ) -> None:
        self.obj_def_getter = obj_def_getter
        self._output_cache: dict[AddrStr, ObjectLayer] = {
            k: v for k, v in BUILTINS_BY_ADDR.items()
        }
        super().__init__()

    def get_obj_layer(self, addr: AddrStr) -> ObjectLayer:
        """Returns the ObjectLayer for a given address."""
        if addr not in self._output_cache:
            obj_def = self.obj_def_getter(addr)
            obj = self.make_object(obj_def)
            assert isinstance(obj, ObjectLayer)
            self._output_cache[addr] = obj
        try:
            return self._output_cache[addr]
        except KeyError as ex:
            raise BlockNotFoundError(f"No block named $addr in {address.get_file(addr)}", addr=addr) from ex

    def make_object(self, obj_def: ObjectDef) -> ObjectLayer:
        """Create an object layer from an object definition."""
        ctx = obj_def.src_ctx
        assert isinstance(ctx, (ap.File_inputContext, ap.BlockdefContext))
        if obj_def.super_ref is not None:
            super_addr = lookup_obj_in_closure(obj_def, obj_def.super_ref)
            super = self.get_obj_layer(super_addr)
        else:
            super = None

        # FIXME: visiting the block here relies upon the fact that both
        # file inputs and blocks have stmt children to be handled the same way.
        if isinstance(ctx, ap.BlockdefContext):
            ctx_with_stmts = ctx.block()
        else:
            ctx_with_stmts = ctx
        locals_ = self.visitBlock(ctx_with_stmts)

        # TODO: check for name collisions
        data = {ref[0]: v for ref, v in locals_}

        obj = ObjectLayer(
            src_ctx=ctx_with_stmts,  # here we save something that's "block-like"
            obj_def=obj_def,
            super=super,
            data=data,
        )

        return obj

    def visitFile_input(self, ctx: ap.File_inputContext) -> None:
        """I'm not sure how we'd end up here, but if we do, don't go down here"""
        raise RuntimeError("File inputs should not be visited")

    def visitBlockdef(self, ctx: ap.BlockdefContext) -> _Sentinel:
        """Don't go down blockdefs, they're just for defining objects."""
        return NOTHING

    def visitAssign_stmt(self, ctx: ap.Assign_stmtContext) -> KeyOptMap:
        assignable_ctx = ctx.assignable()
        assert isinstance(assignable_ctx, ap.AssignableContext)
        if assignable_ctx.new_stmt():
            # ignore new statements here, we'll deal with them in future layers
            return KeyOptMap.empty()

        assigned_value_ref = self.visitName_or_attr(ctx.name_or_attr())
        if len(assigned_value_ref) > 1:
            # we'll deal with overrides later too!
            return KeyOptMap.empty()

        assigned_value = self.visitAssignable(ctx.assignable())
        return KeyOptMap.from_kv(assigned_value_ref, assigned_value)

    def visitSimple_stmt(
        self, ctx: ap.Simple_stmtContext
    ) -> Iterable[_Sentinel | KeyOptItem]:
        """We have to be selective here to deal with the ignored children properly."""
        if ctx.assign_stmt():
            return super().visitSimple_stmt(ctx)

        return (NOTHING,)


@contextmanager
def _translate_addr_key_errors(ctx: ParserRuleContext):
    try:
        yield
    except KeyError as ex:
        addr = ex.args[0]
        terse_addr = address.get_instance_section(addr)
        raise errors.AtoKeyError.from_ctx(
            ctx, f"Couldn't find {terse_addr}"
        ) from ex


class Lofty(BaseTranslator):
    """Lofty's job is to walk orthogonally down (or really up) the instance tree."""

    def __init__(
        self,
        obj_layer_getter: Callable[[AddrStr], ObjectLayer],
    ) -> None:
        self._output_cache: dict[AddrStr, Instance] = {}
        # known replacements are represented as the reference of the instance
        # to be replaced, and a tuple containing the length of the ref of the
        # thing that called for that replacement, and the object that will replace it
        self._known_replacements: dict[AddrStr, AddrStr] = {}
        self.obj_layer_getter = obj_layer_getter

        self._instance_context_stack: list[AddrStr] = []
        self._obj_context_stack: list[AddrStr] = []
        super().__init__()

    def get_instance_tree(self, addr: AddrStr) -> Instance:
        """Return an instance object represented by the given address."""
        if address.get_instance_section(addr):
            raise NotImplementedError

        if addr not in self._output_cache:
            obj_layer = self.obj_layer_getter(addr)
            self.make_instance(addr, obj_layer)
            assert isinstance(self._output_cache[addr], Instance)
        return self._output_cache[addr]

    @contextmanager
    def enter_instance(self, instance: AddrStr):
        """TODO:"""
        self._instance_context_stack.append(instance)
        try:
            yield
        finally:
            self._instance_context_stack.pop()

    @contextmanager
    def enter_obj(self, instance: AddrStr):
        """TODO:"""
        self._obj_context_stack.append(instance)
        try:
            yield
        finally:
            self._obj_context_stack.pop()

    @contextmanager
    def apply_replacements_from_objs(
        self, objs: Iterable[ObjectLayer]
    ) -> Iterable[AddrStr]:
        """
        Apply the replacements defined in the given objects,
        returning which replacements were applied
        """
        commanded_replacements = []

        for obj in objs:
            for ref, replacement in obj.obj_def.replacements.items():
                to_be_replaced_addr = address.add_instances(self._instance_context_stack[-1], ref)
                if to_be_replaced_addr not in self._known_replacements:
                    replace_with_addr = lookup_obj_in_closure(
                        obj.obj_def,
                        replacement.new_super_ref,
                    )

                    self._known_replacements[to_be_replaced_addr] = replace_with_addr
                    commanded_replacements.append(to_be_replaced_addr)
        try:
            yield
        finally:
            for ref in commanded_replacements:
                self._known_replacements.pop(ref)

    def make_instance(self, new_addr: AddrStr, super_obj: ObjectLayer) -> None:
        """Create an instance from a reference and a super object layer."""
        # FIXME: this should deal with name collisions and type collisions

        supers = list(recurse(lambda x: x.super, super_obj))
        override_data: dict[str, Any] = {}
        data = ChainMap(override_data, *[s.data for s in supers])
        new_instance = self._output_cache[new_addr] = Instance(
            addr=new_addr,
            override_data=override_data,
            data=data,
            supers=supers,
        )

        if self._instance_context_stack:
            # eg. we're not to the root
            parent_addr = self._instance_context_stack[-1]
            parent_instance = self._output_cache[parent_addr]
            child_addr = address.get_name(new_addr)
            parent_instance.children[child_addr] = new_instance

        try:
            with ExitStack() as stack:
                stack.enter_context(self.enter_instance(new_addr))
                stack.enter_context(self.apply_replacements_from_objs(supers))
                for super_obj_ in reversed(supers):
                    stack.enter_context(self.enter_obj(super_obj_.address))
                    if super_obj_.src_ctx is None:
                        # FIXME: this is currently the case for the builtins
                        continue

                    # visit the internals (eg. all the new statements, overrides etc...)
                    # of the things we're inheriting from
                    self.visitBlock(super_obj_.src_ctx)
        except Exception:
            self._output_cache.pop(new_addr)
            raise

    def visitBlockdef(self, ctx: ap.BlockdefContext) -> _Sentinel:
        """Don't go down blockdefs, they're just for defining objects."""
        return NOTHING

    def visitAssign_stmt(self, ctx: ap.Assign_stmtContext) -> KeyOptMap:
        """Assignments override values and create new instance of things."""
        assigned_ref = self.visitName_or_attr(ctx.name_or_attr())

        assigned_name: str = assigned_ref[-1]
        assignable_ctx = ctx.assignable()
        assert isinstance(assignable_ctx, ap.AssignableContext)

        # Handle New Statements
        # FIXME: this is a giant fucking mess
        if assignable_ctx.new_stmt():
            new_stmt = assignable_ctx.new_stmt()
            assert isinstance(new_stmt, ap.New_stmtContext)
            if len(assigned_ref) != 1:
                raise errors.AtoError(
                    "Cannot assign a new object to a multi-part reference"
                )

            new_class_ref = self.visitName_or_attr(new_stmt.name_or_attr())

            new_addr = address.add_instance(
                self._instance_context_stack[-1], assigned_name
            )

            if new_addr in self._known_replacements:
                actual_super = self.obj_layer_getter(self._known_replacements[new_addr])
            else:
                try:
                    current_obj_def = self.obj_layer_getter(
                        self._obj_context_stack[-1]
                    ).obj_def
                    new_class_addr = lookup_obj_in_closure(
                        current_obj_def, new_class_ref
                    )
                except KeyError as ex:
                    raise errors.AtoKeyError.from_ctx(
                        current_obj_def.src_ctx, f"Couldn't find ref {new_class_ref}"
                    ) from ex
                try:
                    actual_super = self.obj_layer_getter(new_class_addr)
                except (BlockNotFoundError, errors.AtoFileNotFoundError) as ex:
                    ex.set_src_from_ctx(ctx)
                    raise ex

            # Create and register the new instance to the output cache
            self.make_instance(new_addr, actual_super)
            return KeyOptMap.empty()

        # Handle Overrides

        # We've already dealt with direct assignments in the previous layer
        if len(assigned_ref) == 1:
            return KeyOptMap.empty()

        assigned_value = self.visitAssignable(ctx.assignable())
        instance_addr_assigned_to = address.add_instances(
            self._instance_context_stack[-1], assigned_ref[:-1]
        )
        with _translate_addr_key_errors(ctx):
            instance_assigned_to = self._output_cache[instance_addr_assigned_to]

        instance_assigned_to.override_data[assigned_name] = assigned_value

        return KeyOptMap.empty()

    def visit_pin_or_signal_helper(
        self, ctx: ap.Pindef_stmtContext | ap.Signaldef_stmtContext
    ) -> AddrStr:
        """This function makes a pin or signal instance and sticks it in the instance tree."""
        # NOTE: name has to come first because both have names,
        # but only pins have a "totally an integer"
        ref = self.visit_ref_helper(ctx.name() or ctx.totally_an_integer())
        assert len(ref) == 1  # TODO: unwrap these refs, now they're always one long
        if not ref:
            raise errors.AtoError("Pins must have a name")

        current_instance_addr = self._instance_context_stack[-1]
        current_instance = self._output_cache[current_instance_addr]
        new_addr = address.add_instances(current_instance_addr, ref)

        super_ = PIN if isinstance(ctx, ap.Pindef_stmtContext) else SIGNAL

        override_data: dict[str, Any] = {}
        pin_or_signal = Instance(
            src_ctx=ctx,
            addr=new_addr,
            supers=[super_],
            override_data=override_data,
            data=ChainMap(override_data, super_.data),
        )

        self._output_cache[new_addr] = current_instance.children[ref[0]] = pin_or_signal

        return new_addr

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
        source_addr = self.visitConnectable(ctx.connectable(0))
        target_addr = self.visitConnectable(ctx.connectable(1))

        current_instance_addr = self._instance_context_stack[-1]
        current_instance = self._output_cache[current_instance_addr]

        with _translate_addr_key_errors(ctx):
            source_instance = self._output_cache[source_addr]
            target_instance = self._output_cache[target_addr]

        link = Link(
            src_ctx=ctx,
            parent=current_instance,
            source=source_instance,
            target=target_instance,
        )

        current_instance.links.append(link)

        return KeyOptMap.empty()

    def visitConnectable(self, ctx: ap.ConnectableContext) -> AddrStr:
        """TODO:"""
        if ctx.name_or_attr() or ctx.numerical_pin_ref():
            ref = self.visit_ref_helper(ctx.name_or_attr() or ctx.numerical_pin_ref())
            return address.add_instances(self._instance_context_stack[-1], ref)
        elif ctx.pindef_stmt() or ctx.signaldef_stmt():
            return self.visitChildren(ctx)
        else:
            raise ValueError("Unexpected context in visitConnectable")

    def visitSimple_stmt(self, ctx: ap.Simple_stmtContext) -> KeyOptMap:
        """We have to be selective here to deal with the ignored children properly."""
        if ctx.assign_stmt() or ctx.connect_stmt():
            return super().visitSimple_stmt(ctx)

        elif ctx.pindef_stmt() or ctx.signaldef_stmt():
            self.visitChildren(ctx)

        return KeyOptMap.empty()


scoop = Scoop(parser.get_ast_from_file, [])
dizzy = Dizzy(scoop.get_obj_def)
lofty = Lofty(dizzy.get_obj_layer)


def set_search_paths(paths: Iterable[Path | str]) -> None:
    """Set the search paths for the scoop."""
    scoop.search_paths = paths
