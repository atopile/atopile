"""
This datamodel represents the lowest level of the circuit compilation chain, closest to the hardware.

"""

# TODO: should we make multiple "pins" for a single physical pin?
# eg. there's the pin (pin 3 say on the package), there's the pin
# that's jtag and there's the pin that's i2c, even though they're
# all on the same net

# TODO: we need to be able to define nets

from attrs import define, field
from typing import List, Tuple, Optional, Union

@define
class ModelNode:
    source: str
    locn_start: int
    locn_end: int

@define
class Net(ModelNode):
    name: str

@define
class Pin(ModelNode):
    name: str
    pad: str  # the reference of the copper pad on the board

@define
class Function(ModelNode):
    eqn: str

@define
class Limit(ModelNode):
    eqn: str

@define
class Type(ModelNode):
    name: str
    parents: List['Type'] = field(factory=list)

@define
class State(ModelNode):
    name: str
    functions: List[Function] = field(factory=list)
    limits: List[Limit] = field(factory=list)
    type: Type

@define
class Feature(ModelNode):
    name: str
    nets: List[Pin] = field(factory=list)
    types: List[Type] = field(factory=list)
    functions: List[Function] = field(factory=list)
    limits: List[Limit] = field(factory=list)
    states: List[State] = field(factory=list)
    connections: List[Tuple[str, str]] = field(factory=list)
    inherits_from: List['Feature'] = field(factory=list)

@define
class Package:
    name: str
    pins: List[Pin] = field(factory=list)

@define
class Component(ModelNode):
    # name of the physical component or part
    # eg. U1 or esp32...
    name: str

    nets: List[Net] = field(factory=list)
    functions: List[Function] = field(factory=list)
    types: List[Type] = field(factory=list)
    limits: List[Limit] = field(factory=list)
    states: List[State] = field(factory=list)
    features: List[Feature] = field(factory=list)
    connections: List[Tuple[str, str]] = field(factory=list)
    subcomponents: List['Component'] = field(factory=list)
    inherits_from: List['Component'] = field(factory=list)
    package: Optional[Package]

@define
class Connection(ModelNode):
    between: List[Union[Net, Pin]] = field(factory=list)
