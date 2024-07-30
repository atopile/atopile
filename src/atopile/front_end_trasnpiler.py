"""
This datamodel represents the code in a clean, simple and traversable way,
but doesn't resolve names of things.
In building this datamodel, we check for name collisions, but we don't resolve them yet.
"""

import enum
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from typing import Any, Iterable, Optional

import pint
from antlr4 import ParserRuleContext

from atopile import errors, parse_utils
from atopile.datatypes import KeyOptItem, KeyOptMap, Ref
from atopile.expressions import RangedValue
from atopile.parser.AtopileParser import AtopileParser as ap
from atopile.parser.AtopileParserVisitor import AtopileParserVisitor


class _Sentinel(enum.Enum):
    NOTHING = enum.auto()


NOTHING = _Sentinel.NOTHING


def _get_unit_from_ctx(ctx: ParserRuleContext) -> pint.Unit:
    """Return a pint unit from a context."""
    unit_str = ctx.getText()
    try:
        return pint.Unit(unit_str)
    except pint.UndefinedUnitError as ex:
        raise errors.AtoUnknownUnitError.from_ctx(
            ctx, f"Unknown unit '{unit_str}'"
        ) from ex


class _HandlesPrimaries(AtopileParserVisitor):
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
        if ctx.quantity():
            return self.visitQuantity(ctx.quantity())
        if ctx.bilateral_quantity():
            return self.visitBilateral_quantity(ctx.bilateral_quantity())
        if ctx.bound_quantity():
            return self.visitBound_quantity(ctx.bound_quantity())

        raise ValueError  # this should be protected because it shouldn't be parseable

    def visitQuantity(self, ctx: ap.QuantityContext) -> RangedValue:
        """Yield a physical value from an implicit quantity context."""
        text = ctx.NUMBER().getText()
        if text.startswith("0x"):
            value = int(text, 16)
        else:
            value = float(ctx.NUMBER().getText())

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


class _HandlesGetTypeInfo:
    def _get_type_info(
        self, ctx: ap.Declaration_stmtContext | ap.Assign_stmtContext
    ) -> Optional[pint.Unit]:
        """Return the type information from a type_info context."""
        if type_ctx := ctx.type_info():
            return type_ctx.name_or_attr().getText()
        return None


class _HandleStmtsFunctional(AtopileParserVisitor):
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
                    for _ in child_result:
                        pass
                    if child_result is not NOTHING:
                        yield child_result

        chained_results = []
        for val in __visit():
            chained_results.extend(val)

        # child_results = chain.from_iterable(__visit())
        # child_results = list(child_results)
        child_results = list(item for item in chained_results if item is not NOTHING)
        child_results = KeyOptMap(KeyOptItem(cr) for cr in child_results)

        return KeyOptMap(child_results)

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


@dataclass
class IRComponent:
    @dataclass
    class IRParam:
        name: str | None = None
        value: Any = None

    @dataclass
    class IRInterfaces:
        name: str | None = None
        children_ifs: list["IRComponent.IRInterfaces"] = dataclass_field(
            default_factory=list
        )
        pin_connections: list["IRComponent.IRInterfaces"] = dataclass_field(
            default_factory=list
        )
        params: list["IRComponent.IRParam"] = dataclass_field(default_factory=list)

    @dataclass
    class IRPin(IRInterfaces): ...

    @dataclass
    class IRSignal(IRInterfaces): ...

    name: str | None = None
    footprint_name: str | None = None
    lcsc_id: str | None = None
    children_ifs: list[IRInterfaces] = dataclass_field(default_factory=list)
    params: list[IRParam] = dataclass_field(default_factory=list)
    designator_prefix: str = "U"


class Lofty(_HandleStmtsFunctional, _HandlesPrimaries, _HandlesGetTypeInfo):
    """Lofty's job is to walk orthogonally down (or really up) the instance tree."""

    def __init__(
        self,
    ) -> None:
        self.objs: list[IRComponent] = []
        super().__init__()

    @property
    def current_obj(self) -> IRComponent:
        return self.objs[-1]

    def visitBlockdef(self, ctx: ap.BlockdefContext) -> _Sentinel:
        """Don't go down blockdefs, they're just for defining objects."""
        self.objs.append(IRComponent(name=ctx.name().getText()))
        self.visitChildren(ctx)
        return NOTHING

    def handle_new_assignment(self, ctx: ap.Assign_stmtContext) -> KeyOptMap:
        """Specifically handle "something = new XYZ" assignments."""
        raise NotImplementedError
        return KeyOptMap.empty()

    def visitDeclaration_stmt(self, ctx: ap.Declaration_stmtContext) -> KeyOptMap:
        """Handle declaration statements."""
        # TODO: create TBD
        self.current_obj.params.append(
            IRComponent.IRParam(
                name=ctx.name().getText(),
                value=None,  # None indicates TBD
            )
        )
        return KeyOptMap.empty()

    def visitAssign_stmt(self, ctx: ap.Assign_stmtContext) -> KeyOptMap:
        """Assignment values and create new instance of things."""
        assigned_ref = self.visitName_or_attr(ctx.name_or_attr())

        assignable_ctx = ctx.assignable()
        assert isinstance(assignable_ctx, ap.AssignableContext)

        ########## Handle New Statements ##########
        if assignable_ctx.new_stmt():
            return self.handle_new_assignment(ctx)

        ########## Handle Actual Assignments ##########
        # Figure out what Instance object the assignment is being made to
        if len(assigned_ref) > 1:
            raise NotImplementedError

        assigned_name: str = assigned_ref[-1]
        assignable = self.visit(assignable_ctx)

        if isinstance(assignable, RangedValue):
            si_units = [
                "",
                "volt",
                "ohm",
                "ampere",
                "watt",
                "hertz",
                "farad",
                "henry",
                "second",
            ]

            si_units_map = {
                pint.Unit(unit_str).dimensionality: pint.Unit(unit_str)
                for unit_str in si_units
            }

            if assignable.unit.dimensionality in si_units_map:
                base_val = assignable.to(si_units_map[assignable.unit.dimensionality])
            else:
                base_val = assignable

            assignable = f"F.Range({base_val.min_val}, {base_val.max_val})"
        else:
            assignable = repr(assignable)

        match (assigned_name):
            case "footprint":
                self.current_obj.footprint_name = assignable
            case "lcsc_id":
                self.current_obj.lcsc_id = assignable
            case "designator_prefix":
                self.current_obj.designator_prefix = assignable
            case _:
                self.current_obj.params.append(
                    IRComponent.IRParam(
                        name=assigned_name,
                        value=assignable,
                    )
                )

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
        if ctx.name():
            name = ctx.name().getText()
        elif ctx.string():
            name = ctx.string().getText()
        elif ctx.totally_an_integer():
            name = ctx.totally_an_integer().getText()
        else:
            raise NotImplementedError

        self.current_obj.children_ifs.append(IRComponent.IRPin(name=name))
        return KeyOptMap.from_kv(name, name)

    def visitSignaldef_stmt(self, ctx: ap.Signaldef_stmtContext) -> KeyOptMap:
        """TODO:"""
        name = ctx.name().getText()
        self.current_obj.children_ifs.append(IRComponent.IRSignal(name=name))
        return KeyOptMap.from_kv(name, name)

    def visitConnect_stmt(self, ctx: ap.Connect_stmtContext) -> KeyOptMap:
        """
        Connect interfaces together
        """
        # Attach the pins connected to an interface
        lhs = self.visitConnectable(ctx.connectable(0))[0][0]
        rhs = self.visitConnectable(ctx.connectable(1))[0][0]

        def _lookup(
            listy: list[IRComponent.IRInterfaces], name: str
        ) -> IRComponent.IRInterfaces:
            for li in listy:
                if li.name == name:
                    return li

        lhs_if = _lookup(self.current_obj.children_ifs, lhs)
        rhs_if = _lookup(self.current_obj.children_ifs, rhs)

        lhs_if.pin_connections.append(rhs_if)
        rhs_if.pin_connections.append(lhs_if)
        return KeyOptMap.empty()

    def visitConnectable(self, ctx: ap.ConnectableContext) -> KeyOptMap:
        """Return the address of the connectable object."""
        if ctx.name_or_attr():
            ref = self.visit_ref_helper(ctx.name_or_attr())
            assert len(ref) == 1
            return KeyOptMap.from_kv(ref[0], ref[0])

        if ctx.numerical_pin_ref():
            raise NotImplementedError

        return self.visitChildren(ctx)

    # The following statements are handled exclusively by Dizzy
    def visitRetype_stmt(self, ctx: ap.Retype_stmtContext | Any):
        raise NotImplementedError
        return KeyOptMap.empty()

    def visitImport_stmt(self, ctx: ap.Import_stmtContext | Any):
        raise NotImplementedError
        return KeyOptMap.empty()

    def visitDep_import_stmt(self, ctx: ap.Dep_import_stmtContext | Any):
        raise NotImplementedError
        return KeyOptMap.empty()

    def visitAssert_stmt(self, ctx: ap.Assert_stmtContext) -> KeyOptMap:
        """Handle assertion statements."""
        raise NotImplementedError
        return KeyOptMap.empty()
