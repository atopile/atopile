"""
This module provides a convenient model for accessing atopile models and data.
"""

from itertools import chain

import atopile.address
import atopile.cli.build
import atopile.config
import atopile.datatypes
import atopile.instance_methods
from atopile.address import AddrStr
from atopile.expressions import RangedValue


__all__ = ["build", "Model", "Interface", "Component", "RangedValue"]


class Model(object):
    """This is shim for convenient accessors on the instance class for the minute."""

    def __init__(
        self,
        addr: AddrStr,
        children: dict[str, "Model"],
        interface: dict[str, "Model"],
        attrs: dict,
    ) -> None:
        self._addr = addr
        self._children = children
        self._interface = interface
        self._attrs = attrs

    def get_children(self) -> dict["Model"]:
        return self._children

    def get_interfaces(self) -> dict[str, "Model"]:
        return self._interface

    def get_attributes(self) -> dict[str, "Model"]:
        return self._attrs

    def __getattr__(self, name: str):
        raise AttributeError(f"{self._addr} has no attribute {name}")


class Interface(Model):
    """This is a shim for convenient accessors on the interface class for the minute."""


class Component(Model):
    """This is a shim for convenient accessors on the component class for the minute."""


def _match_interfacey(addr: AddrStr) -> bool:
    """Return True if the address is an interface."""
    return (
        atopile.instance_methods.match_interfaces(addr)
        or atopile.instance_methods.match_pins_and_signals(addr)
    )


def build(addr: AddrStr) -> Model:
    """Build a model from the given address."""
    # Validate the addr
    if not atopile.address.get_entry(addr):
        raise ValueError("The provided address is not a valid entry point.")
    if atopile.address.get_instance_section(addr):
        raise ValueError("The provided address is not a valid entry point.")

    # Configure project context
    project_config = atopile.config.get_project_config_from_addr(addr)
    project_ctx = atopile.config.ProjectContext.from_config(project_config)
    atopile.config.set_project_context(project_ctx)
    build_names = list(project_config.builds)
    if not build_names:
        raise NotImplementedError("There must be SOME build config in your ato configuration file.")
    build_ctx = atopile.config.BuildContext.from_config_name(project_config, build_names[0])
    build_ctx.entry = addr

    # Execute general build steps
    atopile.cli.build.do_prebuild(build_ctx)

    return _construct_model(addr)


def _construct_model(addr: AddrStr) -> Model:
    # Build the models
    children = {}
    interfaces = {}
    attrs = atopile.instance_methods.get_data_dict(addr)

    for child_addr in atopile.instance_methods.get_children(addr):
        child = _construct_model(child_addr)
        name = atopile.address.get_name(child_addr)
        if _match_interfacey(child_addr):
            interfaces[name] = child
        else:
            children[name] = child

    if _match_interfacey(addr):
        base_class = Interface
    elif atopile.instance_methods.match_components(addr):
        base_class = Component
    else:
        base_class = Model

    obj = base_class(
        addr,
        children,
        interfaces,
        attrs
    )

    if set(children) & set(interfaces) & set(attrs):
        raise ValueError("The children and interfaces of an object must be disjoint.")

    for key, value in chain(children.items(), interfaces.items(), attrs.items()):
        setattr(obj, key, value)

    return obj
