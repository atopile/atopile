"""
This datamodel represents the code in a clean, simple and traversable way,
but doesn't resolve names of things.
In building this datamodel, we check for name collisions, but we don't resolve them yet.
"""
import logging
from functools import partial
from typing import Any, Mapping, Optional, Iterable, Type

from antlr4 import ParserRuleContext
from attrs import define, field, resolve_types

from .datatypes import KeyOptMap, Ref


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


@define
class Base:
    """Base class for all objects in the datamodel."""

    # this is optional only because it makes testing convenient
    src_ctx: Optional[ParserRuleContext] = field(default=None, kw_only=True, eq=False)


@define
class Link(Base):
    """Represent a connection between two connectable things."""

    source_ref: Ref
    target_ref: Ref

    source_obj: Optional["Object"] = None
    target_obj: Optional["Object"] = None
    source_node: Optional["Object"] = None
    target_node: Optional["Object"] = None


@define
class Replace(Base):
    """Represent a replacement of one object with another."""

    original_ref: Ref
    replacement_ref: Ref

    # FIXME: I haven't finished planning how to represent this yet


@define
class Import(Base):
    """Represent an import statement."""

    what_ref: Ref
    from_name: str

    what_obj: Optional["Object"] = None


@define
class Object(Base):
    """Represent a container class."""

    supers_refs: tuple[Ref]
    locals_: KeyOptMap

    # these are a shortcut to the named locals - they're the same thing
    # this is here purely for efficiency
    named_locals: Mapping[Ref, Any] = field(init=False)
    unnamed_locals: Iterable[Any] = field(init=False)
    locals_by_type: Mapping[Type, tuple[Ref, Any]] = field(init=False)

    # configured after construction
    closure: Optional[tuple["Object"]] = None

    supers_objs: Optional[tuple["Object"]] = None

    def __attrs_post_init__(self) -> None:
        """Set up the named locals."""
        self.named_locals = self.locals_.get_named_items()
        self.unnamed_locals = self.locals_.get_unnamed_items()
        self.locals_by_type = self.locals_.get_items_by_type((Link, Replace, Import, Object))

    def get_ref_in_locals(self, ref: Ref) -> Any:
        """
        Returns the value of the ref in the locals of the object.
        """
        return self.named_locals[ref]

    def get_ref_in_closure(self, ref: Ref) -> tuple["Object", Any]:
        """
        Get a ref in the current object's closure, returning the object and the value.
        """
        assert isinstance(self.closure, tuple)
        for obj in reversed(self.closure):  # pylint: disable=bad-reversed-sequence
            try:
                return obj, obj.get_ref_in_locals(ref)
            except KeyError:
                pass
        raise KeyError(f"Name '{ref}' not found.")

    def internal_ref_lookup(self, ref: Ref) -> tuple[Any]:
        """
        Look up a ref as a path.

        That is, if given a ref a.b.c; that is find the object
        named a, then b, then c, all internally.

        Returns a tuple of the objects along the path.
        """
        if len(ref) == 0:
            return (self,)

        for lookup_len in reversed(range(1, len(ref))):
            try:
                next_obj = self.get_ref_in_locals(ref[0:lookup_len])
                if len(ref) == 1:
                    return (next_obj,)

                assert isinstance(next_obj, Object)
                return (next_obj,) + next_obj.internal_ref_lookup(ref[lookup_len:])
            except KeyError:
                pass

        raise KeyError(f"Name '{ref}' not found.")

    def closure_ref_path_lookup(self, ref: Ref) -> tuple[Any]:
        """Look up a ref in the closure."""
        if len(ref) == 0:
            return (self,)

        _, next_obj = self.get_ref_in_closure(ref[0:1])
        if len(ref) == 1:
            return (next_obj,)

        assert isinstance(next_obj, Object)
        return next_obj.internal_ref_lookup(ref[1:])[-1]


resolve_types(Link)
resolve_types(Replace)
resolve_types(Import)
resolve_types(Object)


# these are the build-in superclasses that have special meaning to the compiler
MODULE = (Ref.from_one("module"),)
COMPONENT = (Ref.from_one("component"),)

PIN = (Ref.from_one("pin"),)
SIGNAL = (Ref.from_one("signal"),)
INTERFACE = (Ref.from_one("interface"),)


root_object = partial(Object, supers_refs=(), locals_=KeyOptMap(()), closure=())
BUILTINS = {
    MODULE: root_object(),
    COMPONENT: root_object(),
    PIN: root_object(),
    SIGNAL: root_object(),
    INTERFACE: root_object(),
}
