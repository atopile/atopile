"""
This datamodel represents the lowest level of the circuit compilation chain, closest to the hardware.

"""

# TODO: should we make multiple "pins" for a single physical pin?
# eg. there's the pin (pin 3 say on the package), there's the pin
# that's jtag and there's the pin that's i2c, even though they're
# all on the same net

from attrs import define, field
from typing import List, Tuple, Optional

@define
class ModelNode:
    """
    The base class for all nodes in the model
    """
    source: str
    locn_start: int
    locn_end: int

@define
class EtherealPin(ModelNode):
    """
    Represents a pin that is not physically present on the board, any feature or component
    """
    name: str
    type: List['EtherealPin'] = field(default=None)

@define
class Connection(ModelNode):
    """
    Represents the connection between two things

    If a parent is specified, the connection will be represented as a feature whereever possible.

    :param a: the first thing
    :param b: the second thing
    :param parent: (Optional) the feature that causes this connection
    """
    a: EtherealPin
    b: EtherealPin
    parent: Optional['Feature'] = field(default=None)

@define
class Pin(EtherealPin):
    """
    Represents a pin that is phyically present on a device or circuit module

    :param pad: the reference the pad on the package's footprint
    """
    pad: str

@define
class Package:
    """
    Represents a package a component physically comes in.
    eg. QFN-48, SOIC-8, etc...
    """
    name: str
    pins: List[Pin] = field(factory=list)
    footprint: str

@define
class Function(ModelNode):
    """
    Represents a function that controls pin behaviour

    NOTE: this is ultimately mean to represent a mathematical function and should be a richer type.
    It's just currently a string so we can preserve the data somewhere.
    """
    eqn: str

@define
class Limit(ModelNode):
    """
    Represents a limit (a mathematical equality/inequality) a component or feature is subject to

    NOTE: this is ultimately mean to represent a mathematical function and should be a richer type.
    It's just currently a string so we can preserve the data somewhere.
    """
    eqn: str

@define
class State(ModelNode):
    """
    Represents a state of a component or feature
    """
    name: str
    functions: List[Function] = field(factory=list)
    limits: List[Limit] = field(factory=list)
    type: List['EtherealPin'] = field(default=None)

@define
class Feature(ModelNode):
    """
    Represent an abstraction of some function offered by a component or circuit.
    eg. i2c, jtag, power_in etc...

    Assets defined in a feature only exist (and become both accessible and mandatory) when a feature is enabled.
    """
    name: str
    ethereal_pins: List[EtherealPin] = field(factory=list)
    type: List['Feature'] = field(default=None)
    functions: List[Function] = field(factory=list)
    limits: List[Limit] = field(factory=list)
    states: List[State] = field(factory=list)
    connections: List[Tuple[str, str]] = field(factory=list)
    subcomponents: List['Component'] = field(factory=list)

@define
class Component(Feature):
    """
    Represents either a stand-alone electrical component or a circuit module.

    subcomponents and package are mutually exclusive.
    You know what physically exists because it's a subcomponent of the top-level component.
    eg. it has populated        : package  | subcomponents
                                -----------+--------------
        on "type" tree          :  class   |   class
        on "subcomponents" tree : physical |   class
    """
    type: List['Component'] = field(default=None)
    ethereal_pins: List[EtherealPin] = field(factory=list)
    features: List[Feature] = field(factory=list)
    package: Optional[Package]
