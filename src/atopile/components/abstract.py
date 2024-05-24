"""
Module to interact with the component server.
"""

from typing import Optional, TypeVar

from pydantic import BaseModel, ValidationError

import atopile.config
import atopile.errors
import atopile.front_end
from atopile.address import AddrStr
from atopile.front_end import RangedValue
from atopile.instance_methods import get_data
from atopile.components import server_api


# why is this not defined in errors?
class MissingData(atopile.errors.AtoError):
    """
    Raised when a component is missing data in the Basic_Parts.csv file.
    """


class NoMatchingComponent(atopile.errors.AtoError):
    """
    Raised when there's no component matching the given parameters in jlc_parts.csv
    """

    title = "No component matches parameters"


class Component(BaseModel):
    __type__ = None  # Must be replaced in subclasses

    address: AddrStr

    mpn: Optional[str]
    footprint: Optional[str] = None
    package: Optional[str] = None

    def to_query(self) -> BaseModel:
        """
        Convert the component to a query object.
        """
        raise NotImplementedError


T = TypeVar("T", bound=Component)
_type_name_to_ato_map: dict[str, Component] = {}


def _register_ato_type(cls: T) -> T:
    _type_name_to_ato_map[cls.__type__] = cls
    return cls


@_register_ato_type
class Resistor(Component):
    """Resistor component model."""

    __type__ = "resistor"
    value: Optional[RangedValue] = None
    rated_power: Optional[RangedValue] = None
    rated_temp: RangedValue = None

    def to_query(self) -> server_api.ResistorInput:
        value_ohms = self.value.to("ohms")
        rated_temp_c = self.rated_temp.to("celsius")

        return server_api.ResistorInput(
            address=self.address,
            resistance_ohms_min=value_ohms.min_val,
            resistance_ohms_max=value_ohms.max_val,
            rated_temp_celsius_min=rated_temp_c.min_val,
            rated_temp_celsius_max=rated_temp_c.max_val,
        )


def get_specd_value(addr: AddrStr) -> str:
    """
    Return the MPN for a component given its address
    """
    try:
        return str(get_data(addr, "value"))
    except KeyError as ex:
        raise MissingData("$addr has no value", title="No value", addr=addr) from ex


def construct_ato_model(ato_data: dict) -> Component:
    """Make an API query from an ato data dictionary."""
    # In this case the component isn't generic, and there's no MPN provided
    # which means the user has neglected to provide one. We can't do anything
    # TODO: does this shove the error in the middle of querying the value, for
    # example? Shouldn't we be able to get the value independently of the MPN?
    if "__type__" not in ato_data:
        raise NotImplementedError

    type_name = ato_data["__type__"]

    if type_name not in _type_name_to_ato_map:
        raise atopile.errors.AtoTypeError(f"Unknown component type: {type_name}")

    ato_type = _type_name_to_ato_map[type_name]

    # Find the schema for the API schema for the component
    try:
        return ato_type(**ato_data)
    except ValidationError as ex:
        raise atopile.errors.AtoError(f"Invalid component data: {ex}")
