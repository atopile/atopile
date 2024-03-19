"""
This datamodel represents the code in a clean, simple and traversable way,
but doesn't resolve names of things.
In building this datamodel, we check for name collisions, but we don't resolve them yet.
"""

import enum
import operator
from collections import defaultdict, deque
from contextlib import ExitStack, contextmanager
from itertools import chain
from numbers import Number
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Optional

import pint
from antlr4 import ParserRuleContext
from attrs import define, field, resolve_types

from atopile import address, config, errors, expressions
from atopile.address import AddrStr
from atopile.datatypes import KeyOptItem, KeyOptMap, Ref, StackList
from atopile.generic_methods import recurse
from atopile.parse import parser
from atopile.parse_utils import get_src_info_from_ctx
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
class ClassDef(Base):
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

    local_defs: Mapping[Ref, "ClassDef"]
    replacements: Mapping[Ref, Replacement]

    # attached immediately to the object post construction
    closure: Optional[tuple["ClassDef"]] = None  # in order of lookup
    address: Optional[AddrStr] = None

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.address}>"


class RangedValue(expressions.RangedValue):
    def __init__(
        self,
        val_a: Number | pint.Quantity,
        val_b: Number | pint.Quantity,
        unit: Optional[pint.Unit] = None,
        src_ctx: Optional[ParserRuleContext] = None,
    ):
        self.src_ctx = src_ctx
        super().__init__(val_a, val_b, unit)


class Expression(expressions.Expression):
    def __init__(
        self,
        symbols: set[str],
        lambda_: Callable,
        src_ctx: Optional[ParserRuleContext] = None
    ):
        super().__init__(symbols=symbols, lambda_=lambda_)
        self.src_ctx = src_ctx

    def __repr__(self) -> str:
        if not self.src_ctx:
            return f"<{self.__class__.__name__}>"

        return f"<{self.__class__.__name__} {str(self)}>"

    def __str__(self) -> str:
        return self.src_ctx.getText()


class Assertion:
    def __init__(
        self,
        lhs: expressions.Expression,
        operator: str,
        rhs: expressions.Expression,
        src_ctx: Optional[ParserRuleContext] = None,
    ):
        self.lhs = lhs
        self.operator = operator
        self.rhs = rhs
        self.src_ctx = src_ctx

    def __str__(self) -> str:
        return f"{self.lhs} {self.operator} {self.rhs}"


_dimensionality_to_unit_map = {
    "None": pint.Unit("dimensionless"),
    "length": pint.Unit("m"),
    "time": pint.Unit("s"),
    "voltage": pint.Unit("V"),
    "current": pint.Unit("A"),
    "resistance": pint.Unit("ohm"),
    "capacitance": pint.Unit("F"),
    "inductance": pint.Unit("H"),
    "frequency": pint.Unit("Hz"),
    "power": pint.Unit("W"),
    "energy": pint.Unit("J"),
    "charge": pint.Unit("C"),
}


@define
class Assignment(Base):
    """Represent an assignment statement."""

    name: str
    value: Optional[Any]
    given_type: Optional[str | pint.Unit]

    @property
    def unit(self) -> pint.Unit:
        """Return a pint unit from an assignment, or raise an exception if there's no unit."""
        if self.given_type is None:
            # Handle an implicit type
            try:
                return self.value.unit
            except AttributeError as ex:
                raise errors.AtoTypeError(
                    f"Assignment '{self.name}' has no unit"
                ) from ex
        try:
            return _dimensionality_to_unit_map[self.given_type]
        except KeyError as ex:
            raise errors.AtoUnknownUnitError(
                f"Unknown dimensionality '{self.given_type}'"
            ) from ex

    def __repr__(self) -> str:
        return f"<Assignment {self.name} = {self.value}>"


@define(repr=False)
class ClassLayer(Base):
    """
    Represent a layer in the object hierarchy.
    This holds all the values assigned to the object.
    """

    # information about where this object is found in multiple forms
    # this is redundant with one another (eg. you can compute one from the other)
    # but it's useful to have all of them for different purposes
    obj_def: ClassDef

    # None indicates that this is a root object
    super: Optional["ClassLayer"]

    # the local objects and vars are things we navigate to a lot
    assignments: Mapping[str, Assignment]

    @property
    def address(self) -> AddrStr:
        return self.obj_def.address

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.obj_def.address}>"


resolve_types(ClassLayer)


## The below datastructures are created from the above data-model as a second stage


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
    supers: list["ClassLayer"]
    assignments: Mapping[str, deque[Assignment]]
    parent: Optional["Instance"]

    # created as supers' ASTs are walked
    assertions: list[Assertion] = field(factory=list)
    children: dict[str, "Instance"] = field(factory=dict)
    links: list[Link] = field(factory=list)

    def __repr__(self) -> str:
        return f"<Instance {self.addr}>"

    @classmethod
    def from_super(
        cls,
        addr: AddrStr,
        super_: ClassLayer,
        parent: Optional["Instance"],
        src_ctx: Optional[ParserRuleContext] = None,
    ) -> "Instance":
        """Create an instance from a list of supers."""
        supers = list(recurse(lambda x: x.super, super_))

        assignments = defaultdict(deque)

        for super_ in supers:
            for k, v in super_.assignments.items():
                assignments[k].append(v)

        return cls(
            src_ctx=src_ctx,
            addr=addr,
            supers=supers,
            assignments=assignments,
            parent=parent,
        )


resolve_types(Instance)
resolve_types(Link)


class _Sentinel(enum.Enum):
    NOTHING = enum.auto()


NOTHING = _Sentinel.NOTHING


def _make_obj_layer(address: AddrStr, super: Optional[ClassLayer] = None) -> ClassLayer:
    """Create a new object layer from an address and a set of supers."""
    obj_def = ClassDef(
        address=address,
        super_ref=Ref.empty(),
        imports={},
        local_defs={},
        replacements={},
    )
    return ClassLayer(
        obj_def=obj_def,
        super=super,
        assignments={},
    )


MODULE: ClassLayer = _make_obj_layer(AddrStr("<Built-in>:Module"))
COMPONENT: ClassLayer = _make_obj_layer(AddrStr("<Built-in>:Component"), super=MODULE)
PIN: ClassLayer = _make_obj_layer(AddrStr("<Built-in>:Pin"))
SIGNAL: ClassLayer = _make_obj_layer(AddrStr("<Built-in>:Signal"))
INTERFACE: ClassLayer = _make_obj_layer(AddrStr("<Built-in>:Interface"))


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


class HandlesPrimaries(AtopileParserVisitor):
    """
    This class is a mixin to be used with the translator classes.
    """
    def visit_ref_helper(
        self,
        ctx: (
            ap.NameContext
            | ap.AttrContext
            | ap.Name_or_attrContext
            | ap.Totally_an_integerContext
        ),
    ) -> Ref:
        """
        Visit any referencey thing and ensure it's returned as a reference
        """
        return Ref(ctx.getText().split("."))

    def visitName_or_attr(self, ctx: ap.Name_or_attrContext) -> Ref:
        if ctx.name():
            name = self.visitName(ctx.name())
            return Ref.from_one(name)
        elif ctx.attr():
            return self.visitAttr(ctx.attr())

        raise errors.AtoError("Expected a name or attribute")

    def visitName(self, ctx: ap.NameContext) -> str:
        """
        If this is an int, convert it to one (for pins), else return the name as a string.
        """
        return ctx.getText()

    def visitAttr(self, ctx: ap.AttrContext) -> Ref:
        return Ref(self.visitName(name) for name in ctx.name())

    def visitString(self, ctx: ap.StringContext) -> str:
        return ctx.getText().strip("\"'")

    def visitBoolean_(self, ctx: ap.Boolean_Context) -> bool:
        return ctx.getText().lower() == "true"

    def visitLiteral_physical(self, ctx: ap.Literal_physicalContext) -> RangedValue:
        """Yield a physical value from a physical context."""
        if ctx.implicit_quantity():
            return self.visitImplicit_quantity(ctx.implicit_quantity())
        if ctx.bilateral_quantity():
            return self.visitBilateral_quantity(ctx.bilateral_quantity())
        if ctx.bound_quantity():
            return self.visitBound_quantity(ctx.bound_quantity())

        raise ValueError  # this should be protected because it shouldn't be parseable

    def visitImplicit_quantity(self, ctx: ap.Implicit_quantityContext) -> RangedValue:
        """Yield a physical value from an implicit quantity context."""
        value = float(ctx.NUMBER().getText())

        if ctx.name():
            unit = _get_unit_from_ctx(ctx.name())
        else:
            unit = pint.Unit("")

        return RangedValue(
            src_ctx=ctx,
            val_a=value,
            val_b=value,
            unit=unit,
        )

    def visitBilateral_quantity(self, ctx: ap.Bilateral_quantityContext) -> RangedValue:
        """Yield a physical value from a bilateral quantity context."""
        nominal = float(ctx.bilateral_nominal().NUMBER().getText())

        if ctx.bilateral_nominal().name():
            unit = _get_unit_from_ctx(ctx.bilateral_nominal().name())
        else:
            unit = pint.Unit("")

        tol_ctx: ap.Bilateral_toleranceContext = ctx.bilateral_tolerance()
        tol_num = float(tol_ctx.NUMBER().getText())

        if tol_ctx.PERCENT():
            tol_divider = 100
        # FIXME: hardcoding this seems wrong, but the parser/lexer wasn't picking up on it
        elif tol_ctx.name() and tol_ctx.name().getText() == "ppm":
            tol_divider = 1e6
        else:
            tol_divider = None

        if tol_divider:
            if nominal == 0:
                raise errors.AtoError.from_ctx(
                    tol_ctx,
                    "Can't calculate tolerance percentage of a nominal value of zero",
                )

            # In this case, life's a little easier, and we can simply multiply the nominal
            return RangedValue(
                src_ctx=ctx,
                val_a=nominal * (1 - tol_num / tol_divider),
                val_b=nominal * (1 + tol_num / tol_divider),
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

            return RangedValue(
                src_ctx=ctx,
                val_a=nominal - tolerance,
                val_b=nominal + tolerance,
                unit=unit,
            )

        # If there's no unit or percent, then we have a simple tolerance in the same units
        # as the nominal
        return RangedValue(
            src_ctx=ctx,
            val_a=nominal - tol_num,
            val_b=nominal + tol_num,
            unit=unit,
        )

    def visitBound_quantity(self, ctx: ap.Bound_quantityContext) -> RangedValue:
        """Yield a physical value from a bound quantity context."""

        def _parse_end(
            ctx: ap.Quantity_endContext,
        ) -> tuple[float, Optional[pint.Unit]]:
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

        return RangedValue(
            src_ctx=ctx,
            val_a=start_val,
            val_b=end_val,
            unit=unit,
        )


class HandleStmtsFunctional(AtopileParserVisitor):
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

        def __visit():
            for err_cltr, child in errors.iter_through_errors(children):
                with err_cltr():
                    child_result = self.visit(child)
                    if child_result is not NOTHING:
                        yield child_result

        child_results = chain.from_iterable(__visit())
        child_results = list(item for item in child_results if item is not NOTHING)
        child_results = KeyOptMap(KeyOptItem(cr) for cr in child_results)

        return KeyOptMap(child_results)

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


# TODO: actually capture src_ctx on expressions
class Roley(HandlesPrimaries):
    """
    Roley is a green road roller who loves to make up songs and often ends his
    sentences with "Rock and Roll!" He is enthusiastic and works alongside Bob
    and the rest of the team on various construction projects. Roley's main job
    is to smooth out roads and pavements, making sure they are flat and safe
    for everyone. He takes great pride in creating perfect surfaces and is an
    essential member of Bob's team, helping to complete construction tasks with
    his unique abilities.

    Roley's also builds expressions.
    """
    def __init__(self, addr: AddrStr) -> None:
        self.addr = addr
        super().__init__()

    def visitArithmetic_expression(
        self, ctx: ap.Arithmetic_expressionContext
    ) -> expressions.NumericishTypes:
        if ctx.ADD():
            return expressions.defer_operation_factory(
                self.visit(ctx.arithmetic_expression()),
                operator.add,
                self.visit(ctx.term()),
            )

        if ctx.MINUS():
            return expressions.defer_operation_factory(
                self.visit(ctx.arithmetic_expression()),
                operator.sub,
                self.visit(ctx.term()),
            )

        return self.visit(ctx.term())

    def visitTerm(self, ctx: ap.TermContext) -> expressions.NumericishTypes:
        if ctx.STAR():  # multiply
            return expressions.defer_operation_factory(
                self.visit(ctx.term()),
                operator.mul,
                self.visit(ctx.factor()),
            )

        if ctx.DIV():
            return expressions.defer_operation_factory(
                self.visit(ctx.term()),
                operator.truediv,
                self.visit(ctx.factor()),
            )

        return self.visit(ctx.factor())

    def visitFactor(self, ctx: ap.FactorContext) -> expressions.NumericishTypes:
        # Ignore the unary plus operator

        if ctx.MINUS():
            return operator.neg(self.visit(ctx.power()))

        return self.visit(ctx.power())

    def visitPower(self, ctx: ap.PowerContext) -> expressions.NumericishTypes:
        if ctx.factor():
            return expressions.defer_operation_factory(
                self.visit(ctx.atom()),
                operator.pow,
                self.visit(ctx.factor()),
            )

        return self.visit(ctx.atom())

    def visitAtom(self, ctx: ap.AtomContext) -> expressions.NumericishTypes:
        if ctx.arithmetic_group():
            return self.visit(ctx.arithmetic_group().arithmetic_expression())

        if ctx.literal_physical():
            return self.visit(ctx.literal_physical())

        if ctx.name_or_attr():
            return expressions.Symbol(
                address.add_instances(
                    self.addr,
                    self.visit_ref_helper(ctx.name_or_attr()),
                )
            )

        raise ValueError


class Scoop(HandleStmtsFunctional, HandlesPrimaries):
    """Scoop's job is to map out all the object definitions in the code."""

    def __init__(
        self,
        ast_getter: Callable[[str | Path], ParserRuleContext],
    ) -> None:
        self.ast_getter = ast_getter
        self._output_cache: dict[AddrStr, ClassDef] = {}
        super().__init__()

    def get_search_paths(self) -> Iterable[Path]:
        """Return the search paths."""
        project_context = config.get_project_context()
        return [project_context.src_path, project_context.module_path]

    def ingest_file(self, file: str | Path) -> set[AddrStr]:
        """Ingest a file into the cache."""
        # TODO: should this have some protections on
        # things that are already indexed?
        file_ast = self.ast_getter(file)
        obj = self.visitFile_input(file_ast)
        assert isinstance(obj, ClassDef)
        # this operation puts it and it's children in the cache
        return self._register_obj_tree(obj, AddrStr(file), ())

    def get_obj_def(self, addr: AddrStr) -> ClassDef:
        """Returns the ObjectDef for a given address."""
        if addr not in self._output_cache:
            file = address.get_file(addr)
            self.ingest_file(file)
        try:
            return self._output_cache[addr]
        except KeyError as ex:
            raise BlockNotFoundError(
                f"No block named $addr in {address.get_file(addr)}", addr=addr
            ) from ex

    def _register_obj_tree(
        self, obj: ClassDef, addr: AddrStr, closure: tuple[ClassDef]
    ) -> set[AddrStr]:
        """Register address info to the object, and add it to the cache."""
        obj.address = addr
        obj.closure = closure
        child_closure = (obj,) + closure
        self._output_cache[addr] = obj

        addrs: set[AddrStr] = {addr}

        for ref, child in obj.local_defs.items():
            assert len(ref) == 1
            assert isinstance(ref[0], str)
            child_addr = address.add_entry(addr, ref[0])
            addrs |= self._register_obj_tree(child, child_addr, child_closure)

        return addrs

    def visitFile_input(self, ctx: ap.File_inputContext) -> ClassDef:
        """Visit a file input and return it's object."""
        locals_ = self.visit_iterable_helper(ctx.stmt())

        # FIXME: clean this up, and do much better name collision detection on it
        local_defs = {}
        imports = {}
        for ref, local in locals_:
            if isinstance(local, ClassDef):
                local_defs[ref] = local
            elif isinstance(local, Import):
                assert ref is not None
                imports[ref] = local
            else:
                raise errors.AtoError(f"Unexpected local type: {type(local)}")

        file_obj = ClassDef(
            src_ctx=ctx,
            super_ref=Ref.from_one("MODULE"),
            imports=imports,
            local_defs=local_defs,
            replacements={},
        )

        return file_obj

    def visitBlockdef(self, ctx: ap.BlockdefContext) -> KeyOptItem[ClassDef]:
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
            if isinstance(local, ClassDef):
                local_defs[ref] = local
            elif isinstance(local, Import):
                imports[ref] = local
            elif isinstance(local, Replacement):
                replacements[ref] = local
            else:
                raise errors.AtoError(f"Unexpected local type: {type(local)}")

        block_obj = ClassDef(
            src_ctx=ctx,
            super_ref=block_super_ref,
            imports=imports,
            local_defs=local_defs,
            replacements=replacements,
        )

        block_name = self.visit_ref_helper(ctx.name())

        return KeyOptItem.from_kv(block_name, block_obj)

    def _do_import(
        self, ctx: ParserRuleContext, from_file: str, what_refs: list[str]
    ) -> KeyOptMap:
        """Return the import objects created by import statements."""

        _errors = []

        if not from_file:
            _errors.append(
                errors.AtoError("Expected a 'from <file-path>' after 'import'")
            )

        # get the current working directory
        current_file, *_ = get_src_info_from_ctx(ctx)
        current_file = Path(current_file)
        if current_file.is_file():
            search_paths = chain((current_file.parent,), self.get_search_paths())
        else:
            search_paths = self.get_search_paths()

        for search_path in search_paths:
            candidate_path: Path = (search_path / from_file).resolve().absolute()
            if candidate_path.exists():
                break
        else:
            raise errors.AtoImportNotFoundError.from_ctx(  # pylint: disable=raise-missing-from
                ctx, f"File '{from_file}' not found."
            )

        imports = {}
        for _what_ref in what_refs:
            if not _what_ref:
                _errors.append(
                    errors.AtoError(
                        "Expected a name or attribute to import after 'import'"
                    )
                )

            if _what_ref == "*":
                # import everything
                raise NotImplementedError("import *")

            import_addr = address.add_entries(str(candidate_path), _what_ref)

            imports[_what_ref] = Import(
                src_ctx=ctx,
                obj_addr=import_addr,
            )

        return KeyOptMap(KeyOptItem.from_kv(k, v) for k, v in imports.items())

    def visitImport_stmt(self, ctx: ap.Import_stmtContext) -> KeyOptMap:
        """
        Updated import statement: from "abcd.ato" import xyz
        """
        from_file: str = self.visitString(ctx.string())
        what_refs = [
            self.visit_ref_helper(name_of_attr) for name_of_attr in ctx.name_or_attr()
        ]
        return self._do_import(ctx, from_file, what_refs)

    def visitDep_import_stmt(self, ctx: ap.Dep_import_stmtContext) -> KeyOptMap:
        """
        DEPRECATED: import xyz from "abcd.ato"
        """
        from_file: str = self.visitString(ctx.string())
        import_what_ref = self.visit_ref_helper(ctx.name_or_attr())
        return self._do_import(ctx, from_file, [import_what_ref])

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
        if ctx.retype_stmt() or ctx.import_stmt() or ctx.dep_import_stmt():
            return super().visitSimple_stmt(ctx)

        return KeyOptMap.empty()


def lookup_class_in_closure(context: ClassDef, ref: Ref) -> AddrStr:
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


class Dizzy(HandleStmtsFunctional, HandlesPrimaries):
    """
    Dizzy is responsible for creating object layers, mixing cement,
    sand, aggregate, and water to create concrete.
    Ref.: https://www.youtube.com/watch?v=drBge9JyloA
    """

    def __init__(
        self,
        obj_def_getter: Callable[[AddrStr], ClassDef],
    ) -> None:
        self.obj_def_getter = obj_def_getter
        self._output_cache: dict[AddrStr, ClassLayer] = {
            k: v for k, v in BUILTINS_BY_ADDR.items()
        }
        self.class_def_scope: StackList[ClassDef] = StackList()
        super().__init__()

    def get_layer(self, addr: AddrStr) -> ClassLayer:
        """Returns the ObjectLayer for a given address."""
        if addr not in self._output_cache:
            obj_def = self.obj_def_getter(addr)
            obj = self.build_layer(obj_def)
            assert isinstance(obj, ClassLayer)
            self._output_cache[addr] = obj
        try:
            return self._output_cache[addr]
        except KeyError as ex:
            raise BlockNotFoundError(
                f"No block named $addr in {address.get_file(addr)}", addr=addr
            ) from ex

    def _get_supers_layer(self, cls_def: ClassDef) -> Optional[ClassLayer]:
        """Return the super object of a given object."""
        if cls_def.super_ref is not None:
            super_addr = lookup_class_in_closure(cls_def, cls_def.super_ref)
            return self.get_layer(super_addr)
        return None

    def build_layer(self, cls_def: ClassDef) -> ClassLayer:
        """Create an object layer from an object definition."""
        ctx = cls_def.src_ctx
        assert isinstance(ctx, (ap.File_inputContext, ap.BlockdefContext))

        # NOTE: visiting the block here relies upon the fact that both
        # file inputs and blocks have stmt children to be handled the same way.
        if isinstance(ctx, ap.BlockdefContext):
            ctx_with_stmts = ctx.block()
        else:
            ctx_with_stmts = ctx

        with self.class_def_scope.enter(cls_def):
            locals_ = self.visitBlock(ctx_with_stmts)

        strainer = locals_.strain()

        obj = ClassLayer(
            src_ctx=ctx_with_stmts,  # here we save something that's "block-like"
            obj_def=cls_def,
            super=self._get_supers_layer(cls_def),
            assignments={
                ref[0]: v for ref, v in strainer.strain(lambda x: isinstance(x.value, Assignment))
            }
        )

        if strainer:
            raise RuntimeError(f"Unexpected items in ClassLayer locals: {', '.join(strainer)}")

        return obj

    def visitFile_input(self, ctx: ap.File_inputContext) -> None:
        """I'm not sure how we'd end up here, but if we do, don't go down here"""
        raise RuntimeError("File inputs should not be visited")

    def visitBlockdef(self, ctx: ap.BlockdefContext) -> _Sentinel:
        """Don't go down blockdefs, they're just for defining objects."""
        return NOTHING

    def _get_type_info(self, ctx: ap.Declaration_stmtContext | ap.Assign_stmtContext) -> Optional[ClassLayer | pint.Unit]:
        """Return the type information from a type_info context."""
        if type_ctx := ctx.type_info():
            return type_ctx.name_or_attr().getText()
        return None

        # TODO: parse types properly
        if type_info := ctx.type_info():
            assert isinstance(type_info, ap.Type_infoContext)
            type_info_str: str = type_info.name_or_attr().getText()

            try:
                return lookup_class_in_closure(
                    self.class_def_scope.top,
                    type_info_str,
                )
            except KeyError:
                pass

            # TODO: implement types for ints, floats, strings, etc.
            # voltages, currents, lengths etc...

        return None

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

        assignment = Assignment(
            src_ctx=ctx,
            name=assigned_value_ref[0],
            value=self.visitAssignable(assignable_ctx),
            given_type=self._get_type_info(ctx),
        )
        return KeyOptMap.from_kv(assigned_value_ref, assignment)

    def visitDeclaration_stmt(self, ctx: ap.Declaration_stmtContext) -> KeyOptMap:
        """Handle declaration statements."""
        assigned_value_ref = self.visitName_or_attr(ctx.name_or_attr())
        if len(assigned_value_ref) > 1:
            raise errors.AtoSyntaxError(
                f"Can't declare fields in a nested object {assigned_value_ref}"
            )

        assignment = Assignment(
            src_ctx=ctx,
            name=assigned_value_ref[0],
            value=None,
            given_type=self._get_type_info(ctx),
        )
        return KeyOptMap.from_kv(assigned_value_ref, assignment)

    def visitSimple_stmt(
        self, ctx: ap.Simple_stmtContext
    ) -> Iterable[_Sentinel | KeyOptItem]:
        """We have to be selective here to deal with the ignored children properly."""
        if ctx.assign_stmt() or ctx.declaration_stmt():
            return super().visitSimple_stmt(ctx)

        return (NOTHING,)


@contextmanager
def _translate_addr_key_errors(ctx: ParserRuleContext):
    try:
        yield
    except KeyError as ex:
        addr = ex.args[0]
        terse_addr = address.get_instance_section(addr)
        raise errors.AtoKeyError.from_ctx(ctx, f"Couldn't find {terse_addr}") from ex


class Lofty(HandleStmtsFunctional, HandlesPrimaries):
    """Lofty's job is to walk orthogonally down (or really up) the instance tree."""

    def __init__(
        self,
        obj_layer_getter: Callable[[AddrStr], ClassLayer],
    ) -> None:
        self._output_cache: dict[AddrStr, Instance] = {}
        # known replacements are represented as the reference of the instance
        # to be replaced, and a tuple containing the length of the ref of the
        # thing that called for that replacement, and the object that will replace it
        self._known_replacements: dict[AddrStr, AddrStr] = {}
        self.obj_layer_getter = obj_layer_getter

        self._instance_addr_stack: StackList[AddrStr] = StackList()
        self._class_addr_stack: StackList[AddrStr] = StackList()
        super().__init__()

    @property
    def _current_instance(self) -> Instance:
        """Return the current instance."""
        return self._output_cache[self._instance_addr_stack.top]

    def get_instance(self, addr: AddrStr) -> Instance:
        """Return an instance object represented by the given address."""
        if addr in self._output_cache:
            return self._output_cache[addr]

        if address.get_instance_section(addr):
            # Trigger build of the tree above the instance
            self.get_instance(address.get_entry(addr))

        obj_layer = self.obj_layer_getter(addr)
        self.build_instance(addr, obj_layer)
        assert isinstance(self._output_cache[addr], Instance)

        return self._output_cache[addr]

    @contextmanager
    def apply_replacements_from_objs(
        self, objs: Iterable[ClassLayer]
    ) -> Iterable[AddrStr]:
        """
        Apply the replacements defined in the given objects,
        returning which replacements were applied
        """
        commanded_replacements = []

        for obj in objs:
            for ref, replacement in obj.obj_def.replacements.items():
                to_be_replaced_addr = address.add_instances(
                    self._instance_addr_stack.top, ref
                )
                if to_be_replaced_addr not in self._known_replacements:
                    replace_with_addr = lookup_class_in_closure(
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

    def check_name_uniqueness(self, name: str, current_scope: Instance):
        """Check if the given name is unique within the current scope."""
        if current_scope is None:
            # If there's no current scope, we're at a global level where the check might not be applicable
            return
        if name in current_scope.children:
            raise errors.AtoError(f"Name '{name}' is already used in this scope. Address: {current_scope.addr}")


    def build_instance(self, new_addr: AddrStr, super_obj: ClassLayer, src_ctx: Optional[ParserRuleContext] = None) -> None:
        """Create an instance from a reference and a super object layer."""

        if self._instance_addr_stack:
            # eg. we're not to the root
            parent_instance = self._output_cache[self._instance_addr_stack.top]
        else:
            # eg. we're at the root
            parent_instance = None

        instance_name = address.get_name(new_addr)
        self.check_name_uniqueness(instance_name, parent_instance)

        new_instance = Instance.from_super(
            new_addr,
            super_obj,
            parent=parent_instance,
            src_ctx=src_ctx
        )
        self._output_cache[new_addr] = new_instance

        if self._instance_addr_stack:
            child_addr = address.get_name(new_addr)
            parent_instance.children[child_addr] = new_instance

        try:
            with ExitStack() as stack:
                stack.enter_context(self._instance_addr_stack.enter(new_addr))
                stack.enter_context(self.apply_replacements_from_objs(new_instance.supers))
                for super_obj_ in reversed(new_instance.supers):
                    stack.enter_context(self._class_addr_stack.enter(super_obj_.address))
                    if super_obj_.src_ctx is None:
                        # FIXME: this is currently the case for the builtins
                        continue

                    # visit the internals (eg. all the new statements, overrides etc...)
                    # of the things we're inheriting from
                    self.visitBlock(super_obj_.src_ctx)
        except Exception:
            if new_addr in self._output_cache:
                del self._output_cache[new_addr]
            raise

    def visitBlockdef(self, ctx: ap.BlockdefContext) -> _Sentinel:
        """Don't go down blockdefs, they're just for defining objects."""
        return NOTHING

    def handle_new_assignment(self, ctx: ap.Assign_stmtContext) -> KeyOptMap:
        """Specifically handle "something = new XYZ" assignments."""
        assigned_ref = self.visitName_or_attr(ctx.name_or_attr())

        assigned_name: str = assigned_ref[-1]
        assignable_ctx = ctx.assignable()
        assert isinstance(assignable_ctx, ap.AssignableContext)

        # FIXME: this is a giant fucking mess
        new_stmt = assignable_ctx.new_stmt()
        assert isinstance(new_stmt, ap.New_stmtContext)
        if len(assigned_ref) != 1:
            raise errors.AtoError(
                "Cannot assign a new object to a multi-part reference"
            )

        new_class_ref = self.visitName_or_attr(new_stmt.name_or_attr())

        new_addr = address.add_instance(
            self._instance_addr_stack.top, assigned_name
        )

        # Figure out what class to create the new instance from
        if new_addr in self._known_replacements:
            actual_super = self.obj_layer_getter(self._known_replacements[new_addr])
        else:
            try:
                current_obj_def = self.obj_layer_getter(
                    self._class_addr_stack.top
                ).obj_def
                new_class_addr = lookup_class_in_closure(
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
        self.build_instance(new_addr, actual_super, ctx)
        return KeyOptMap.empty()

    def visitAssign_stmt(self, ctx: ap.Assign_stmtContext) -> KeyOptMap:
        """Assignments override values and create new instance of things."""
        assigned_ref = self.visitName_or_attr(ctx.name_or_attr())

        assigned_name: str = assigned_ref[-1]
        assignable_ctx = ctx.assignable()
        assert isinstance(assignable_ctx, ap.AssignableContext)

        ########## Handle New Statements ##########
        if assignable_ctx.new_stmt():
            return self.handle_new_assignment(ctx)

        ########## Handle Overrides ##########

        # We've already dealt with direct assignments in the previous layer
        if len(assigned_ref) == 1:
            return KeyOptMap.empty()

        instance_addr_assigned_to = address.add_instances(
            self._instance_addr_stack.top, assigned_ref[:-1]
        )
        with _translate_addr_key_errors(ctx):
            instance_assigned_to = self._output_cache[instance_addr_assigned_to]

        # TODO: de-triplicate this
        if type_info := ctx.type_info():
            given_type = lookup_class_in_closure(
                self.obj_layer_getter(self._class_addr_stack.top).obj_def,
                type_info.name_or_attr()
            )
        else:
            given_type = None

        assignment = Assignment(
            src_ctx=ctx,
            name=assigned_name,
            value=self.visitAssignable(assignable_ctx),
            given_type=given_type,
        )

        instance_assigned_to.assignments[assigned_name].appendleft(assignment)

        return KeyOptMap.empty()

    def visit_pin_or_signal_helper(
        self, ctx: ap.Pindef_stmtContext | ap.Signaldef_stmtContext
    ) -> AddrStr:
        """This function makes a pin or signal instance and sticks it in the instance tree."""
        # NOTE: name has to come first because both have names,
        # but only pins have a "totally an integer"
        name = (ctx.name() or ctx.totally_an_integer()).getText()

        current_instance_addr = self._instance_addr_stack.top
        current_instance = self._output_cache[current_instance_addr]
        new_addr = address.add_instance(current_instance_addr, name)

        super_ = PIN if isinstance(ctx, ap.Pindef_stmtContext) else SIGNAL

        pin_or_signal = Instance.from_super(
            src_ctx=ctx,
            addr=new_addr,
            super_=super_,
            parent=current_instance,
        )

        self._output_cache[new_addr] = current_instance.children[name] = pin_or_signal

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

        with _translate_addr_key_errors(ctx):
            source_instance = self._output_cache[source_addr]
            target_instance = self._output_cache[target_addr]

        link = Link(
            src_ctx=ctx,
            parent=self._current_instance,
            source=source_instance,
            target=target_instance,
        )

        self._current_instance.links.append(link)

        return KeyOptMap.empty()

    def visitConnectable(self, ctx: ap.ConnectableContext) -> AddrStr:
        """TODO:"""
        if ctx.name_or_attr() or ctx.numerical_pin_ref():
            ref = self.visit_ref_helper(ctx.name_or_attr() or ctx.numerical_pin_ref())
            return address.add_instances(self._instance_addr_stack.top, ref)
        elif ctx.pindef_stmt() or ctx.signaldef_stmt():
            return self.visitChildren(ctx)
        else:
            raise ValueError("Unexpected context in visitConnectable")

    def visitSimple_stmt(self, ctx: ap.Simple_stmtContext) -> KeyOptMap:
        """We have to be selective here to deal with the ignored children properly."""
        if ctx.assign_stmt() or ctx.connect_stmt() or ctx.assert_stmt():
            return super().visitSimple_stmt(ctx)

        elif ctx.pindef_stmt() or ctx.signaldef_stmt():
            self.visitChildren(ctx)

        return KeyOptMap.empty()

    def visitAssert_stmt(self, ctx: ap.Assert_stmtContext) -> KeyOptMap:
        """Handle assertion statements."""
        comparison_ctx: ap.ComparisonContext = ctx.comparison()
        roley = Roley(self._instance_addr_stack.top)

        expressions_ = []
        operators = []

        def _add_expr_from_context(ctx: ap.Arithmetic_expressionContext):
            expr = Expression.from_numericish(
                roley.visit(ctx)
            )
            # TODO: this shouldn't be attached to the expression like this
            # as the only means to pretty-print them
            expr.src_ctx = ctx
            expressions_.append(expr)

        _add_expr_from_context(comparison_ctx.arithmetic_expression())

        for comp_ctx in comparison_ctx.compare_op_pair():
            assert isinstance(comp_ctx, ap.Compare_op_pairContext)
            if child_ctx := comp_ctx.lt_arithmetic_or():
                operators.append("<")
            elif child_ctx := comp_ctx.gt_arithmetic_or():
                operators.append(">")
            elif child_ctx := comp_ctx.in_arithmetic_or():
                operators.append("within")
            else:
                raise ValueError
            _add_expr_from_context(child_ctx.arithmetic_expression())

        assert len(expressions_) == len(operators) + 1

        assertions_ = [Assertion(
            src_ctx=ctx,
            lhs=expressions_[i],
            operator=operators[i],
            rhs=expressions_[i+1],
        ) for i in range(len(operators))]

        self._current_instance.assertions.extend(assertions_)

        return KeyOptMap.empty()




scoop = Scoop(parser.get_ast_from_file)
dizzy = Dizzy(scoop.get_obj_def)
lofty = Lofty(dizzy.get_layer)
