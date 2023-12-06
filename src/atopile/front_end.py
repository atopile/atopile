"""
This datamodel represents the code in a clean, simple and traversable way,
but doesn't resolve names of things.
In building this datamodel, we check for name collisions, but we don't resolve them yet.
"""
import enum
import logging
from collections import ChainMap
from contextlib import contextmanager
from itertools import chain
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

import toolz
from antlr4 import ParserRuleContext

from atopile.address import AddrStr
from atopile import errors
from atopile.datatypes import KeyOptItem, KeyOptMap, Ref
from atopile.generic_methods import recurse
from atopile.parse_utils import get_src_info_from_ctx
from atopile.parser.AtopileParser import AtopileParser as ap
from atopile.parser.AtopileParserVisitor import AtopileParserVisitor

from .datamodel import (
    Import,
    Instance,
    Link,
    LinkDef,
    ObjectDef,
    ObjectLayer,
    Replacement,
)

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class _Sentinel(enum.Enum):
    NOTHING = enum.auto()


NOTHING = _Sentinel.NOTHING



def make_obj_layer(address: AddrStr, super: Optional[ObjectLayer] = None) -> ObjectLayer:
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


# class Spud:
#     def __init__(self, error_handler: errors.ErrorHandler) -> None:
#         self.error_handler = error_handler


class BaseTranslator(AtopileParserVisitor):
    """
    Dizzy is responsible for mixing cement, sand, aggregate, and water to create concrete.
    Ref.: https://www.youtube.com/watch?v=drBge9JyloA
    """

    def __init__(
        self,
        error_handler: errors.ErrorHandler,
    ) -> None:
        self.error_handler = error_handler
        super().__init__()

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
                for item in child_result:
                    if item is not NOTHING:
                        assert isinstance(item, KeyOptItem)
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

    def visitSimple_stmt(self, ctx: ap.Simple_stmtContext) -> Iterable[_Sentinel | KeyOptItem]:
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
            if item is NOTHING:
                return KeyOptMap.empty()
            assert isinstance(item, KeyOptItem)
            return KeyOptMap.from_item(item)

        raise TypeError("Unexpected statement type")

    def visitSimple_stmts(self, ctx: ap.Simple_stmtsContext) -> tuple[list[errors.AtoError], KeyOptMap]:
        return self.visit_iterable_helper(ctx.simple_stmt())

    def visitBlock(self, ctx) -> tuple[list[errors.AtoError], KeyOptMap]:
        if ctx.stmt():
            return self.visit_iterable_helper(ctx.stmt())
        if ctx.simple_stmts():
            return self.visitSimple_stmts(ctx.simple_stmts())
        raise ValueError  # this should be protected because it shouldn't be parseable

    def visitAssignable(
        self, ctx: ap.AssignableContext
    ) -> int | float | str | bool:
        """Yield something we can place in a set of locals."""
        if ctx.name_or_attr():
            raise errors.AtoError(
                "Cannot directly reference another object like this. Use 'new' instead."
            )

        if ctx.NUMBER():
            value = float(ctx.NUMBER().getText())
            return int(value) if value.is_integer() else value

        if ctx.string():
            return self.visitString(ctx)

        if ctx.boolean_():
            return self.visitBoolean_(ctx.boolean_())

        assert not ctx.new_stmt(), "New statements should have already been filtered out."
        raise TypeError(f"Unexpected assignable type {type(ctx)}")


class Scoop(BaseTranslator):
    """Scoop's job is to map out all the object definitions in the code."""
    def __init__(
        self,
        error_handler: errors.ErrorHandler,
        input_map: Mapping[str | Path, ParserRuleContext],
        search_paths: Iterable[Path | str],
    ) -> None:
        self.input_map = input_map
        self.search_paths = search_paths
        self._output_cache: dict[AddrStr, ObjectDef] = {}
        super().__init__(error_handler)

    def __getitem__(self, addr: AddrStr) -> ObjectDef:
        if addr not in self._output_cache:
            assert addr.file is not None
            file_ast = self.input_map[addr.file]
            obj = self.visitFile_input(file_ast)
            assert isinstance(obj, ObjectDef)
            # this operation puts it and it's children in the cache
            self._register_obj_tree(obj, AddrStr(addr.file), ())
        return self._output_cache[addr]

    def _register_obj_tree(self, obj: ObjectDef, addr: AddrStr, closure: tuple[ObjectDef]) -> None:
        """Register address info to the object, and add it to the cache."""
        obj.address = addr
        obj.closure = closure
        child_closure = (obj,) + closure
        self._output_cache[addr] = obj
        for ref, child in obj.local_defs.items():
            assert len(ref) == 1
            assert isinstance(ref[0], str)
            child_addr = addr.add_node(ref[0])
            self._register_obj_tree(child, child_addr, child_closure)

    def visitFile_input(self, ctx: ap.File_inputContext) -> ObjectDef:
        """Visit a file input and return it's object."""
        file_errors, locals_ = self.visit_iterable_helper(ctx.stmt())

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
            errors=file_errors,
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

        block_errors, locals_ = self.visitBlock(ctx.block())

        if block_errors:
            raise errors.AtoFatalError

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
            errors=block_errors,
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
            _errors.append(errors.AtoError("Expected a 'from <file-path>' after 'import'"))
        if not import_what_ref:
            _errors.append(errors.AtoError("Expected a name or attribute to import after 'import'"))

        if import_what_ref == "*":
            # import everything
            raise NotImplementedError("import *")

        # get the current working directory
        current_file, _, _ = get_src_info_from_ctx(ctx)
        try:
            current_file = Path(current_file)
            if current_file.is_file():
                candidate_path = current_file.parent / from_file
                self.input_map[candidate_path]
            else:
                raise TypeError
        except (KeyError, TypeError):
            for search_path in self.search_paths:
                candidate_path = search_path / from_file
                try:
                    self.input_map[candidate_path]
                except KeyError:
                    continue
                else:
                    break
            else:
                raise errors.AtoImportNotFoundError.from_ctx(  # pylint: disable=raise-missing-from
                    f"File '{from_file}' not found.", ctx
                )

        import_addr = AddrStr.from_parts(path=candidate_path, ref=import_what_ref)

        import_ = Import(
            src_ctx=ctx,
            errors=_errors,
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
            errors=[],
            new_super_ref=new_class,
        )

        return KeyOptMap.from_kv(to_replace, replacement)

    def visitSimple_stmt(self, ctx: ap.Simple_stmtContext) -> Iterable[_Sentinel | KeyOptItem]:
        """We have to be selective here to deal with the ignored children properly."""
        if (ctx.retype_stmt() or ctx.import_stmt()):
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
            imp_ref: imp for imp_ref, imp in scope.imports.items() if ref[0] == imp_ref[0]
        }

        if import_leads and obj_lead:
            # TODO: improve error message with details about what items are conflicting
            raise errors.AtoAmbiguousReferenceError.from_ctx(
                f"Name '{ref[0]}' is ambiguous in '{scope}'.",
                scope.src_ctx
            )

        if obj_lead is not None:
            return AddrStr.from_parts(obj_lead.address.file, obj_lead.address.ref + ref[1:])

        if ref in scope.imports:
            return scope.imports[ref].obj_addr

    if ref in BUILTINS_BY_REF:
        return BUILTINS_BY_REF[ref].address

    raise KeyError(ref)


class Dizzy(BaseTranslator):
    """Dizzy's job is to create object layers."""
    def __init__(
        self,
        error_handler: errors.ErrorHandler,
        input_map: Mapping[AddrStr, ObjectDef],
    ) -> None:
        self.input_map = input_map
        self._output_cache: dict[AddrStr, ObjectLayer] = {k: v for k, v in BUILTINS_BY_ADDR.items()}
        super().__init__(error_handler)

    def __getitem__(self, addr: AddrStr) -> ObjectLayer:
        if addr not in self._output_cache:
            obj_def = self.input_map[addr]
            obj = self.make_object(obj_def)
            assert isinstance(obj, ObjectLayer)
            self._output_cache[addr] = obj
        return self._output_cache[addr]

    def make_object(self, obj_def: ObjectDef) -> ObjectLayer:
        """Create an object layer from an object definition."""
        ctx = obj_def.src_ctx
        assert isinstance(ctx, (ap.File_inputContext, ap.BlockdefContext))
        if obj_def.super_ref is not None:
            super_addr = lookup_obj_in_closure(obj_def, obj_def.super_ref)
            super = self[super_addr]
        else:
            super = None

        # FIXME: visiting the block here relies upon the fact that both
        # file inputs and blocks have stmt children to be handled the same way.
        if isinstance(ctx, ap.BlockdefContext):
            ctx_with_stmts = ctx.block()
        else:
            ctx_with_stmts = ctx
        errors_, locals_ = self.visitBlock(ctx_with_stmts)

        if errors_:
            raise errors.AtoFatalError

        # TODO: check for name collisions
        data = {ref[0]: v for ref, v in locals_}

        obj = ObjectLayer(
            src_ctx=ctx_with_stmts,  # here we save something that's "block-like"
            errors=errors_,

            obj_def=obj_def,

            super=super,
            data=data
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

    def visitSimple_stmt(self, ctx: ap.Simple_stmtContext) -> Iterable[_Sentinel | KeyOptItem]:
        """We have to be selective here to deal with the ignored children properly."""
        if ctx.assign_stmt():
            return super().visitSimple_stmt(ctx)

        return (NOTHING,)


class Lofty(BaseTranslator):
    """Lofty's job is to walk orthogonally down (or really up) the instance tree."""
    def __init__(
        self,
        error_handler: errors.ErrorHandler,
        input_map: Mapping[AddrStr, ObjectLayer],
    ) -> None:
        # known replacements are represented as the reference of the instance
        # to be replaced, and a tuple containing the length of the ref of the
        # thing that called for that replacement, and the object that will replace it
        self._known_replacements: dict[Ref, Replacement] = {}
        self.input_map = input_map
        self._output_cache: dict[AddrStr, Instance] = {}
        self._ref_stack: list[Ref] = []
        self._obj_layer_stack: list[ObjectLayer] = []
        super().__init__(
            error_handler,
        )

    def __getitem__(self, addr: AddrStr) -> Instance:
        if addr not in self._output_cache:
            obj_layer = self.input_map[addr]
            obj = self.make_instance(addr.ref, obj_layer)
            assert isinstance(obj, Instance)
            self._output_cache[addr] = obj
        return self._output_cache[addr]

    @contextmanager
    def _context(self, ref: Ref, parent_obj_layer: ObjectLayer):
        self._ref_stack.append(Ref(ref))
        self._obj_layer_stack.append(parent_obj_layer)

        try:
            yield

        finally:
            self._ref_stack.pop()
            self._obj_layer_stack.pop()

    def make_instance(self, new_ref: Ref, super: ObjectLayer) -> Instance:
        """Create an instance from a reference and a super object layer."""
        supers = list(recurse(lambda x: x.super, super))

        commanded_replacements = []
        for super_obj in supers:
            for ref, replacement in super_obj.obj_def.replacements.items():
                abs_ref = new_ref + ref
                if abs_ref not in self._known_replacements:
                    self._known_replacements[abs_ref] = replacement
                    commanded_replacements.append(abs_ref)

        with self._context(new_ref, super):
            # FIXME: can we make this functional easily?
            # FIXME: this should deal with name collisions and type collisions
            _errors = []
            all_internal_items: list[KeyOptItem] = []
            for super in reversed(supers):
                if super.src_ctx is None:
                    # FIXME: this is currently the case for the builtins
                    continue
                internal_errors, internal_items = self.visitBlock(super.src_ctx)
                _errors.extend(internal_errors)
                all_internal_items.extend(internal_items)

        for ref in commanded_replacements:
            self._known_replacements.pop(ref)

        if _errors:
            raise errors.AtoFatalError

        internal_by_type = KeyOptMap(all_internal_items).map_items_by_type(
            [
                Instance,
                LinkDef,
                (str, int, float, bool)
            ]
        )

        children: dict[Ref, Instance] = {k[0]: v for k, v in internal_by_type[Instance]}

        def _lookup_item_in_children(
                _children: dict[Ref, Instance],
                ref: Ref
            ) -> Instance:
            if ref[0] not in _children:
                raise errors.AtoError(f"Unknown reference: {ref}")
            if len(ref) == 1:
                return _children[ref[0]]

            sub_children = _children[ref[0]].children
            return _lookup_item_in_children(
                sub_children,
                ref[1:]
            )

        # make links
        links: list[Link] = []
        for _, link_def in internal_by_type[LinkDef]:
            assert isinstance(link_def, LinkDef)
            source_instance = _lookup_item_in_children(children, link_def.source)
            target_instance = _lookup_item_in_children(children, link_def.target)
            link = Link(
                src_ctx=link_def.src_ctx,
                errors=[],
                parent=source_instance,
                source=source_instance,
                target=target_instance,
            )
            links.append(link)

        for key, value in internal_by_type[(str, int, float, bool)]:
            # TODO: make sure key exists?
            to_override_in = _lookup_item_in_children(children, key[:-1])
            key_name = key[-1]
            to_override_in.override_data[key_name] = value
            to_override_in._override_location[key_name] = super

        # we don't yet know about any of the overrides we may encounter
        # we pre-define this variable so we can stick it in the right slot and in the chain map
        override_data: dict[str, Any] = {}
        data = ChainMap(override_data, *[s.data for s in supers])

        new_instance = Instance(
            errors=_errors,
            ref=new_ref,
            supers=supers,
            children=children,
            links=links,
            data=data,
            override_data=override_data,
        )

        for link in links:
            link.parent = new_instance

        return new_instance

    def visitBlockdef(self, ctx: ap.BlockdefContext) -> _Sentinel:
        """Don't go down blockdefs, they're just for defining objects."""
        return NOTHING

    def visitAssign_stmt(self, ctx: ap.Assign_stmtContext) -> KeyOptMap:
        assigned_ref = self.visitName_or_attr(ctx.name_or_attr())

        assignable_ctx = ctx.assignable()
        assert isinstance(assignable_ctx, ap.AssignableContext)
        if assignable_ctx.new_stmt():
            new_stmt = assignable_ctx.new_stmt()
            assert isinstance(new_stmt, ap.New_stmtContext)
            if len(assigned_ref) != 1:
                raise errors.AtoError("Cannot assign a new object to a multi-part reference")

            new_class_ref = self.visitName_or_attr(new_stmt.name_or_attr())

            object_context = self._obj_layer_stack[-1]

            # FIXME: this is a giant fucking mess
            new_ref = Ref(self._ref_stack[-1] + assigned_ref)

            if new_ref in self._known_replacements:
                super_addr = lookup_obj_in_closure(
                    object_context.obj_def,
                    self._known_replacements[new_ref].new_super_ref
                )
                actual_super = self.input_map[super_addr]
            else:
                try:
                    new_class_addr = lookup_obj_in_closure(
                        self._obj_layer_stack[-1].obj_def, new_class_ref
                    )
                except KeyError as ex:
                    raise errors.AtoKeyError.from_ctx(
                        f"Couldn't find ref {new_class_ref}",
                        ctx
                    ) from ex
                actual_super = self.input_map[new_class_addr]

            new_instance = self.make_instance(new_ref, actual_super)

            return KeyOptMap.from_kv(assigned_ref, new_instance)

        if len(assigned_ref) == 1:
            # we've already dealt with this!
            return KeyOptMap(())

        assigned_value = self.visitAssignable(ctx.assignable())
        return KeyOptMap.from_kv(assigned_ref, assigned_value)

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

        override_data: dict[str, Any] = {}

        pin = Instance(
            src_ctx=ctx,

            ref=Ref(self._ref_stack[-1] + ref),
            supers=(PIN,),
            children={},
            links=[],

            data=override_data,  # FIXME: this should be a chain map
            override_data=override_data,
        )

        return KeyOptMap.from_kv(ref, pin)

    def visitSignaldef_stmt(self, ctx: ap.Signaldef_stmtContext) -> KeyOptMap:
        ref = self.visit_ref_helper(ctx.name())
        if not ref:
            raise errors.AtoError("Signals must have a name")

        override_data: dict[str, Any] = {}

        signal = Instance(
            src_ctx=ctx,

            ref=Ref(self._ref_stack[-1] + ref),
            supers=(SIGNAL,),
            children={},
            links=[],

            data=override_data,  # FIXME: this should be a chain map
            override_data=override_data,
        )

        return KeyOptMap.from_kv(ref, signal)

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

    def visitSimple_stmt(self, ctx: ap.Simple_stmtContext) -> KeyOptMap:
        """We have to be selective here to deal with the ignored children properly."""
        if ctx.assign_stmt() or ctx.connect_stmt() or ctx.pindef_stmt() or ctx.signaldef_stmt():
            return super().visitSimple_stmt(ctx)

        return KeyOptMap.empty()
