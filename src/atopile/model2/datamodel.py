"""
This datamodel represents the code in a clean, simple and traversable way,
but doesn't resolve names of things.
In building this datamodel, we check for name collisions, but we don't resolve them yet.
"""
from collections import ChainMap
from functools import partial
from typing import Any, Iterable, Mapping, Optional, Type

from antlr4 import ParserRuleContext
from attrs import define, field, resolve_types

from atopile.address import AddrStr
from atopile.model2.datatypes import Ref, KeyOptMap


@define
class Base:
    """Represent a base class for all things."""
    src_ctx: Optional[ParserRuleContext] = field(kw_only=True, default=None)
    errors: list[Exception] = field(kw_only=True, factory=list)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"


@define(repr=False)
class Link(Base):
    """Represent a connection between two connectable things."""
    source_ref: Ref
    target_ref: Ref

    def __repr__(self) -> str:
        return super().__repr__() + f" {self.source_ref} -> {self.target_ref}"


@define(repr=False)
class Replace(Base):
    """Represent a replacement of one object with another."""
    original_ref: Ref
    replacement_obj: "Object"


@define(repr=False)
class Import(Base):
    """Represent an import statement."""
    what_obj: "Object"


# NOTE:
#  Perhaps we should consider splitting out instantiated objects from classes?
#  While there's a lot in common between those two things (eg. lookup semantics)
#  there's also some baggage which comes with this model, like that declaring
#  classes within a class mean that you will init the inner class every time
#  you init the outer class.
@define(repr=False)
class Object(Base):
    """Represent a container class."""
    # information about where this object is found in multiple forms
    # this is redundant with one another (eg. you can compute one from the other)
    # but it's useful to have all of them for different purposes
    closure: tuple["Object"]  # in order of lookup
    address: AddrStr
    supers: tuple["Object"]

    # the local objects and vars are things we navigate to a lot
    objs: Optional[Mapping[str, "Object"]] = None
    data: Optional[Mapping[str, Any]] = None
    # TODO: override_data eg. Resistor.footprint = ... to set a default on a module level

    # data used in the construction of objects
    imports: Optional[Mapping[Ref, Import]] = None

    # data from the lock-file entry associated with this object
    # lock_data: Mapping[str, Any] = {}  # TODO: this should point to a lockfile entry

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.address}>"


resolve_types(Link)
resolve_types(Replace)
resolve_types(Import)
resolve_types(Object)


# These are the build-in superclasses that have special meaning to the compiler

root_object = partial(
    Object,
    closure=(),
    objs={},
    data={},
    links=[],
    imports=(),
    replacements=(),
)
MODULE = root_object(address=AddrStr("<Built-in> Module"), supers=())
COMPONENT = root_object(address=AddrStr("<Built-in> Component"), supers=(MODULE,))
PIN = root_object(address=AddrStr("<Built-in> Pin"), supers=())
SIGNAL = root_object(address=AddrStr("<Built-in> Signal"), supers=())
INTERFACE = root_object(address=AddrStr("<Built-in> Interface"), supers=())


## The below datastructures are created from the above datamodel as a second stage


@define
class Joint:
    """Represent a connection between two connectable things."""
    # TODO: we may not need this using loop-soup
    # the reason this currently exists is to allow us to map joints between instances
    # these make sense only in the context of the pins and signals, which aren't
    # language fundamentals as much as net objects - eg. they're useful only from
    # a specific electrical perspective
    origin_link: Link

    contained_by: "Instance"
    source_connected: "Instance"
    target_connected: "Instance"

    source: "Instance"
    target: "Instance"

    def __repr__(self) -> str:
        return f"<Joint {repr(self.source)} -> {repr(self.target)}>"


@define
class Instance:
    """Represent a concrete object class."""
    # origin information
    # much of this information is redundant, however it's all highly referenced
    # so it's useful to have it all at hand
    ref: Ref
    parents: tuple["Instance"]
    super: Object

    children: Optional[Mapping[str, "Instance"]] = None
    data: Optional[Mapping[str, Any]] = None

    # TODO: for later
    # lock_data: Optional[Mapping[str, Any]] = None

    joints: list[Joint] = field(factory=list)
    joined_to_me: list[Joint] = field(factory=list)

    def __repr__(self) -> str:
        return f"<Instance {self.ref}>"


resolve_types(Joint)
resolve_types(Instance)
