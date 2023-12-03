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
    replacement_ref: Ref

    replacement_obj: Optional["Object"] = None


@define(repr=False)
class Import(Base):
    """Represent an import statement."""
    what_ref: Ref
    from_name: str

    what_obj: Optional["Object"] = None


# NOTE:
#  Perhaps we should consider splitting out instantiated objects from classes?
#  While there's a lot in common between those two things (eg. lookup semantics)
#  there's also some baggage which comes with this model, like that declaring
#  classes within a class mean that you will init the inner class every time
#  you init the outer class.
@define(repr=False)
class Object(Base):
    """Represent a container class."""
    # base information required whenever an object is created
    super_ref: Optional[Ref]

    # the local objects and vars are things we navigate to a lot
    objs: Mapping[str, "Object"] = {}
    data: Mapping[str, Any] = {}
    # TODO: override_data eg. Resistor.footprint = ... to set a default on a module level
    links: list[Link] = []

    # data used in the construction of objects
    imports: Mapping[Ref, Import] = {}
    replacements: list[Replace] = []

    # data that modifies children (presumable instances) in this object
    instance_overrides: Mapping[Ref, Any] = {}

    # data from the lock-file entry associated with this object
    lock_data: Mapping[str, Any] = {}  # TODO: this should point to a lockfile entry

    # information about where this object is found in multiple forms
    # this is redundant with one another (eg. you can compute one from the other)
    # but it's useful to have all of them for different purposes
    closure: tuple["Object"] = field(init=False)  # in order of lookup
    ref: Ref = field(init=False)
    address: AddrStr = field(init=False)

    # information attached post-init
    # these are the objects that the super_refs resolve to
    super_obj: Optional["Object"] = None
    # these are the full list of supers (in lookup order) that this object inherits from
    all_supers: Optional[tuple["Object"]] = None

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.address}>"


resolve_types(Link)
resolve_types(Replace)
resolve_types(Import)
resolve_types(Object)


# these are the build-in superclasses that have special meaning to the compiler
MODULE_REF = Ref.from_one("module")
COMPONENT_REF = Ref.from_one("component")
PIN_REF = Ref.from_one("pin")
SIGNAL_REF = Ref.from_one("signal")
INTERFACE_REF = Ref.from_one("interface")


root_object = partial(Object, supers_refs=None, locals_=KeyOptMap(()), closure=())
MODULE = root_object(address=AddrStr("<Built-in> Module"))
COMPONENT = Object(supers_refs=(MODULE_REF,), locals_=KeyOptMap(()), closure=())
PIN = root_object(address=AddrStr("<Built-in> Pin"))
SIGNAL = root_object(address=AddrStr("<Built-in> Signal"))
INTERFACE = root_object(address=AddrStr("<Built-in> Interface"))

BUILTINS = {
    MODULE_REF: MODULE,
    COMPONENT_REF: COMPONENT,
    PIN_REF: PIN,
    SIGNAL_REF: SIGNAL,
    INTERFACE_REF: INTERFACE,
}


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
    address: AddrStr
    ref: Ref
    parents: tuple["Instance"] = field(init=False)

    origin: Object = field(init=False)
    super: Object = field(init=False)

    children: Mapping[str, "Instance"] = field(init=False)
    data: Mapping[str, Any] = field(init=False)

    override_data: Mapping[str, Any] = field(init=False)

    lock_data: Mapping[str, Any] = field(init=False)

    joints: list[Joint] = field(factory=list)
    joined_to_me: list[Joint] = field(factory=list)


    def __repr__(self) -> str:
        return f"<Instance {self.ref}>"


resolve_types(Joint)
resolve_types(Instance)
