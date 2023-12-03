"""
This datamodel represents the code in a clean, simple and traversable way,
but doesn't resolve names of things.
In building this datamodel, we check for name collisions, but we don't resolve them yet.
"""
import enum
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, Mapping, Optional

import toolz
from antlr4 import ParserRuleContext

from atopile.address import AddrStr
from atopile.model2 import errors
from atopile.model2.datatypes import KeyOptItem, KeyOptMap, Ref
from atopile.model2.object_methods import lookup_obj_in_closure
from atopile.model2.parse_utils import get_src_info_from_ctx
from atopile.parser.AtopileParser import AtopileParser as ap
from atopile.parser.AtopileParserVisitor import AtopileParserVisitor

from .datamodel import (
    COMPONENT,
    INTERFACE,
    MODULE,
    PIN,
    SIGNAL,
    Base,
    Import,
    LinkDef,
    Object,
    Replace,
    Instance,
)

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class _Sentinel(enum.Enum):
    NOTHING = enum.auto()


NOTHING = _Sentinel.NOTHING


def fill_object(obj: Object, locals_: KeyOptMap) -> None:
    """Fill a provided object Object."""
    # TODO: move this to the object methods
    # somewhere to accumnuulate errors
    _errors = []

    # find name conflicts
    def __get_effective_name(item: KeyOptItem) -> str:
        key, _ = item
        return key

    name_usage = toolz.groupby(__get_effective_name, locals_)
    for name, usages in name_usage.items():
        if len(usages) > 1:
            # TODO: make this error more friendly by listing the things that share this name
            _errors += [errors.AtoNameConflictError.from_ctx(
                f"Conflicting name '{name}'",
                obj.src_ctx
            )]

    # stick all the locals in the right buckets
    for ref, local in locals_:
        try:
            if isinstance(local, Object):
                if len(ref) > 1:
                    raise errors.AtoError(f"Cannot implicitly nest objects: {ref}")
                obj.objs[ref[0]] = local
            elif isinstance(local, Import):
                obj.imports[ref] = local
            # elif isinstance(local, Replace):
            #     obj.replacements.append(local)
            # elif isinstance(local, Link):
            #     if ref:
            #         raise NotImplementedError("Named links not yet supported")
            #     obj.links.append(local)
            elif isinstance(local, (int, float, str, bool)):
                # TODO: make a parameter object
                # TODO: there's something better than ignoring the overrides we can do here
                if len(ref) == 1:
                    obj.data[ref[0]] = local

            else:
                raise errors.AtoTypeError.from_ctx(
                    f"Unknown local type: {type(local)} of {ref}",
                    obj.src_ctx
                )

        except errors.AtoError as err:
            _errors.append(err)

    if _errors:
        obj.errors.extend(_errors)
        raise errors.AtoErrorGroup.from_ctx(
            "Errors occured while filling locals",
            _errors,
            obj.src_ctx
        )

class BaseTranslator(AtopileParserVisitor):
    """
    Dizzy is responsible for mixing cement, sand, aggregate, and water to create concrete.
    Ref.: https://www.youtube.com/watch?v=drBge9JyloA
    """

    def __init__(
        self,
        error_handler: errors.ErrorHandler,
        input_map: Mapping[Path, ParserRuleContext],
    ) -> None:
        self.error_handler = error_handler
        self.input_map = input_map
        self._output_cache: dict[AddrStr, Base] = {}
        self._context_stack: list[tuple[AddrStr, tuple[Base]]] = []
        super().__init__()

    @contextmanager
    def _abs_context(self, addr: AddrStr, context: tuple[Base]) -> None:
        addr = AddrStr(addr)
        self._context_stack.append((addr, context))
        yield
        self._context_stack.pop()

    @contextmanager
    def _relative_context(self, name: str, context: Base) -> None:
        addr, abs_context = self._context_stack[-1]
        with self._abs_context(
            addr.add_node(name),
            abs_context + (context,)
        ):
            yield

    def _get_addr(self) -> AddrStr:
        return self._context_stack[-1][0]

    def _get_context(self) -> tuple[Base]:
        return self._context_stack[-1][1]

    def defaultResult(self):
        """
        Override the default "None" return type
        (for things that return nothing) with the Sentinel NOTHING
        """
        return NOTHING

    def visit_iterable_helper(
        self,
        children: Iterable
    ) -> tuple[list[errors.AtoError], KeyOptMap]:
        """
        Visit multiple children and return a tuple of their results,
        discard any results that are NOTHING and flattening the children's results.
        It is assumed the children are returning their own OptionallyNamedItems.
        """

        _errors = []

        def __visit(child: ParserRuleContext) -> Iterable[_Sentinel | KeyOptItem]:
            try:
                child_result = self.visit(child)
                assert isinstance(child_result, KeyOptMap)
                return child_result
            except errors.AtoError as err:
                _errors.append(err)
                self.error_handler.handle(err)
                return (NOTHING,)

        items: Iterable[KeyOptItem] = toolz.pipe(
            children,                                          # stick in data
            toolz.curried.map(__visit),                        # visit each child
            toolz.curried.concat,                              # flatten the results
            toolz.curried.filter(lambda x: x is not NOTHING),  # filter out nothings
            toolz.curried.map(KeyOptItem)                      # ensure they are all KeyOptItem
        )

        return _errors, KeyOptMap(items)

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
                ap.Numerical_pin_refContext
            ),
        ):
            return Ref.from_one(str(self.visit(ctx)))
        if isinstance(ctx, (ap.AttrContext, ap.Name_or_attrContext)):
            return Ref(
                map(str, self.visit(ctx)),
            )
        raise errors.AtoError(f"Unknown reference type: {type(ctx)}")

    def visitName(self, ctx: ap.NameContext) -> str | int:
        """
        If this is an int, convert it to one (for pins), else return the name as a string.
        """
        try:
            return int(ctx.getText())
        except ValueError:
            return ctx.getText()

    def visitAttr(self, ctx: ap.AttrContext) -> Ref:
        return Ref(self.visitName(name) for name in ctx.name())  # Comprehension

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

    def visitAssignable(
        self, ctx: ap.AssignableContext
    ) -> Object | int | float | str | bool:
        """Yield something we can place in a set of locals."""
        if ctx.name_or_attr():
            raise errors.AtoError(
                "Cannot directly reference another object like this. Use 'new' instead."
            )

        if ctx.new_stmt():
            return self.visitNew_stmt(ctx.new_stmt())

        if ctx.NUMBER():
            value = float(ctx.NUMBER().getText())
            return int(value) if value.is_integer() else value

        if ctx.string():
            return self.visitString(ctx)

        if ctx.boolean_():
            return self.visitBoolean_(ctx.boolean_())

        raise errors.AtoError("Unexpected assignable type")


class Dizzy(BaseTranslator):
    """Dizzy's job is to map out all the objects in the code."""
    def __getitem__(self, addr: AddrStr) -> Object:
        if addr not in self._output_cache:
            file_ast = self.input_map[addr.file]
            self._output_cache[addr] = self.visitFile_input(file_ast)
        return self._output_cache[addr]

    def visitFile_input(self, ctx: ap.File_inputContext) -> Object:
        """Visit a file input and return it's object."""
        file, _, _ = get_src_info_from_ctx(ctx)

        addr = AddrStr.from_parts(path=file)

        file_obj = Object(
            supers=(MODULE,),
            address=addr,
            closure=(),
            src_ctx=ctx,
        )

        with self._abs_context(addr, ()):
            file_errors, locals_ = self.visit_iterable_helper(ctx.stmt())

        file_obj.errors.extend(file_errors)

        fill_object(
            file_obj,
            locals_=locals_,
        )

        self._output_cache[addr] = file_obj
        return file_obj

    def visitBlockdef(self, ctx: ap.BlockdefContext) -> KeyOptItem:
        if ctx.FROM():
            if not ctx.name_or_attr():
                raise errors.AtoSyntaxError("Expected a name or attribute after 'from'")
            block_super_ref = self.visit_ref_helper(ctx.name_or_attr())
            block_super = lookup_obj_in_closure(
                self._context_stack[-1],
                block_super_ref
            )
        else:
            block_super = self.visitBlocktype(ctx.blocktype())

        # TODO: check that that we're using an appropriate block type

        block_name = self.visit_ref_helper(ctx.name())

        addr = self._get_addr().add_node(block_name[0])
        closure = self._get_context()

        obj = Object(
            supers=(block_super,) + block_super.supers,
            src_ctx=ctx,
            address=addr,
            closure=closure,
        )

        with self._relative_context(addr, obj):
            block_errors, block_returns = self.visitBlock(ctx.block())

        obj.errors.extend(block_errors)
        fill_object(
            obj=obj,
            locals_=block_returns,
        )

        self._output_cache[addr] = obj
        return KeyOptItem.from_kv(
            block_name,
            obj,
        )

    def visitAssign_stmt(self, ctx: ap.Assign_stmtContext) -> KeyOptMap:
        assigned_value_ref = self.visitName_or_attr(ctx.name_or_attr())
        if len(assigned_value_ref) > 1 or ctx.assignable().new_stmt():
            return  # we'll deal with overrides and creating new object later!

        assigned_value = self.visitAssignable(ctx.assignable())
        return KeyOptMap.from_kv(assigned_value_ref, assigned_value)

    def visitSimple_stmt(self, ctx: ap.Simple_stmtContext) -> _Sentinel | KeyOptItem:
        """
        This is practically here as a development shim to assert the result is as intended
        """
        result = self.visitChildren(ctx)
        if result is not NOTHING:
            if len(result) > 0:
                assert len(result[0]) == 2
        return result

    def visitStmt(self, ctx: ap.StmtContext) -> KeyOptMap:
        """
        Ensure consistency of return type.
        We choose to raise any below exceptions here, because stmts can be nested,
        and raising exceptions serves as our collection mechanism.
        """
        if ctx.simple_stmts():
            stmt_errors, stmt_returns = self.visitSimple_stmts(ctx.simple_stmts())

            if stmt_errors:
                if len(stmt_errors) == 1:
                    raise stmt_errors[0]
                else:
                    raise errors.AtoErrorGroup.from_ctx(
                        "Errors occured in nested statements",
                        stmt_errors,
                        ctx
                    )

            return stmt_returns
        elif ctx.compound_stmt():
            item = self.visit(ctx.compound_stmt())
            assert isinstance(item, KeyOptItem)
            return KeyOptMap.from_item(item)

        raise TypeError("Unexpected statement type")

    def visitSimple_stmts(self, ctx: ap.Simple_stmtsContext) -> tuple[list[errors.AtoError], KeyOptMap]:
        return self.visit_iterable_helper(ctx.simple_stmt())

    def visitBlocktype(self, ctx: ap.BlocktypeContext) -> Object:
        block_type_name = ctx.getText()
        match block_type_name:
            case "module":
                return MODULE
            case "component":
                return COMPONENT
            case "interface":
                return INTERFACE
            case _:
                raise errors.AtoError(f"Unknown block type '{block_type_name}'")

    def visitBlock(self, ctx) -> tuple[list[errors.AtoError], KeyOptMap]:
        if ctx.simple_stmts():
            return self.visitSimple_stmts(ctx.simple_stmts())
        elif ctx.stmt():
            return self.visit_iterable_helper(ctx.stmt())
        raise ValueError  # this should be protected because it shouldn't be parseable


    # Import statements have no ref
    def visitImport_stmt(self, ctx: ap.Import_stmtContext) -> KeyOptMap:
        from_file: str = self.visitString(ctx.string())
        import_what_ref = self.visit_ref_helper(ctx.name_or_attr())

        _errors = []

        if not from_file:
            _errors.append(errors.AtoError("Expected a 'from <file-path>' after 'import'"))
        if not import_what_ref:
            _errors.append(errors.AtoError("Expected a name or attribute to import after 'import'"))

        if import_what_ref == "*":
            # import everything
            raise NotImplementedError("import *")

        for error in _errors:
            self.error_handler.handle(error)

        import_addr = AddrStr.from_parts(path=from_file, ref=import_what_ref)
        import_what_obj = self[import_addr]

        import_ = Import(
            src_ctx=ctx,
            errors=_errors,
            what_obj=import_what_obj
        )

        return KeyOptMap.from_kv(import_what_ref, import_)


class Lofty(BaseTranslator):
    """Lofty's job is to walk orthogonally to Dizzy, and build the instance tree."""
    def __init__(
        self,
        error_handler: errors.ErrorHandler,
        input_map: Mapping[Path, ParserRuleContext],
    ) -> None:
        # known replacements are represented as the reference of the instance
        # to be replaced, and a tuple containing the length of the ref of the
        # thing that called for that replacement, and the object that will replace it
        self.known_replacements: dict[Ref, tuple[int, Object]] = {}
        super().__init__(
            error_handler,
            input_map
        )

    def make_instance(self, super: Object, src_ctx: ParserRuleContext) -> Instance:
        """Create an instance of an object."""
        ref, 
        return Instance(
            src_ctx=src_ctx,
            errors=[],
            ref=
        )

    def build_from_root(self, root: Object) -> Instance:
        """
        Build an instance from a root object.
        """
        raise NotImplementedError

    def visitAssign_stmt(self, ctx: ap.Assign_stmtContext) -> KeyOptMap:
        assigned_value_name = self.visitName_or_attr(ctx.name_or_attr())
        assigned_value = self.visitAssignable(ctx.assignable())

        return KeyOptMap.from_kv(assigned_value_name, assigned_value)

    def visitTotally_an_integer(self, ctx: ap.Totally_an_integerContext) -> int:
        text = ctx.getText()
        try:
            return int(text)
        except ValueError:
            raise errors.AtoTypeError.from_ctx(f"Expected an integer, but got {text}", ctx)  # pylint: disable=raise-missing-from

    def visitPindef_stmt(self, ctx: ap.Pindef_stmtContext) -> KeyOptMap:
        ref = self.visit_ref_helper(ctx.totally_an_integer() or ctx.name())
        assert len(ref) == 1 # TODO: unwrap these refs, now they're always one long
        if not ref:
            raise errors.AtoError("Pins must have a name")

        pin = Object(
            src_ctx=ctx,
            errors=[],
            closure=self.get_current_closure(),
            address=self.get_current_addr().add_node(ref[0]),
            supers=(PIN,),
            objs={},
            data={},
            links=[],
            imports={},
            replacements=[],
        )

        return KeyOptMap.from_kv(ref, pin)

    def visitSignaldef_stmt(self, ctx: ap.Signaldef_stmtContext) -> KeyOptMap:
        ref = self.visit_ref_helper(ctx.name())
        if not ref:
            raise errors.AtoError("Signals must have a name")

        signal = Object(
            src_ctx=ctx,
            errors=[],
            closure=self.get_current_closure(),
            address=self.get_current_addr().add_node(ref[0]),
            supers=(SIGNAL,),
            objs={},
            data={},
            links=[],
            imports={},
            replacements=[],
        )
        return KeyOptMap.from_kv(ref, signal)

    # if a signal or a pin def statement are executed during a connection, it is returned as well
    def visitConnectable(
        self, ctx: ap.ConnectableContext
    ) -> tuple[Ref, Optional[KeyOptItem]]:
        if ctx.name_or_attr():
            # Returns a tuple
            return self.visit_ref_helper(ctx.name_or_attr()), None
        elif ctx.numerical_pin_ref():
            return self.visit_ref_helper(ctx.numerical_pin_ref()), None
        elif ctx.pindef_stmt() or ctx.signaldef_stmt():
            connectable: KeyOptMap = self.visitChildren(ctx)
            # return the object's ref and the created object itself
            ref = connectable[0][0]
            assert ref is not None
            return ref, connectable[0]
        else:
            raise ValueError("Unexpected context in visitConnectable")

    def visitConnect_stmt(self, ctx: ap.Connect_stmtContext) -> KeyOptMap:
        """
        Connect interfaces together
        """
        source_name, source = self.visitConnectable(ctx.connectable(0))
        target_name, target = self.visitConnectable(ctx.connectable(1))

        returns = [
            KeyOptItem.from_kv(
                None,
                LinkDef(source_name, target_name, src_ctx=ctx),
            )
        ]

        # If the connect statement is also used to instantiate
        # an element, add it to the return tuple
        if source:
            returns.append(source)

        if target:
            returns.append(target)

        return KeyOptMap(returns)

    def visitNew_stmt(self, ctx: ap.New_stmtContext) -> Instance:
        current_ref, current_instance = self._context_stack[-1]
        if current_ref in self.known_replacements:
            _, new_super = self.known_replacements[current_ref]
            class_to_init = new_super

        else:
            class_to_init_ref = self.visit_ref_helper(ctx.name_or_attr())
            assert isinstance(current_instance, Instance)
            class_to_init = lookup_obj_in_closure(
                current_instance.super.closure,
                class_to_init_ref
            )

        return self.make_object(
            super_ref=class_to_init,
            locals_=KeyOptMap(),
            src_ctx=ctx,
        )

    def visitRetype_stmt(self, ctx: ap.Retype_stmtContext) -> None:
        """
        This statement type will replace an existing block with a new one of a subclassed type

        Since there's no way to delete elements, we can be sure that the subclass is
        a superset of the superclass (confusing linguistically, makes sense logically)
        """
        current_ref, current_instance = self._context_stack[-1]
        instance_ref = self.visit_ref_helper(ctx.name_or_attr(0))
        abs_instance_ref = current_ref + instance_ref
        if abs_instance_ref in self.known_replacements:
            existing_prio, _ = self.known_replacements[abs_instance_ref]
            if existing_prio > len(current_ref):
                # we've already replaced this object with something else
                # and that replacement is higher priority than this one
                return

        assert isinstance(current_instance, Instance)
        new_type_name = self.visit_ref_helper(ctx.name_or_attr(1))

        new_super = lookup_obj_in_closure(
            current_instance.super.closure,
            new_type_name
        )

        self.known_replacements[abs_instance_ref] = (
            len(current_ref),
            new_super,
        )
