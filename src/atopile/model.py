"""
This datamodel represents the lowest level of the circuit compilation chain, closest to the hardware.

"""

# TODO: should we make multiple "pins" for a single physical pin?
# eg. there's the pin (pin 3 say on the package), there's the pin
# that's jtag and there's the pin that's i2c, even though they're
# all on the same net

# TODO: we need to be able to define nets

from attrs import define
from typing import List, Tuple, Optional

@define
class ModelNode:
    source: str
    locn_start: int
    locn_end: int

@define
class Pin(ModelNode):
    name: str
    ref: str

@define
class Function(ModelNode):
    eqn: str

@define
class Limit(ModelNode):
    eqn: str

@define
class Type(ModelNode):
    name: str
    parents: List['Type']

@define
class State(ModelNode):
    name: str
    functions: List[Function]
    limits: List[Limit]
    type: Type

@define
class Argument(ModelNode):
    name: str
    unit: str

@define
class Feature(ModelNode):
    name: str
    args: List[Argument]
    pins: List[Pin]
    types: List[Type]
    functions: List[Function]
    limits: List[Limit]
    states: List[State]
    connections: List[Tuple[str, str]]
    inherits_from: List['Feature']

@define
class Package:
    pass

@define
class Component(ModelNode):
    name: str
    args: List[Argument]
    pins: List[Pin]
    functions: List[Function]
    types: List[Type]
    limits: List[Limit]
    states: List[State]
    features: List[Feature]
    connections: List[Tuple[str, str]]
    inherits_from: List['Component']
    package: Optional[Package]

@define
class Connection(ModelNode):
    pins: List[Pin]

@define
class Circuit(ModelNode):
    components: List[Component]
    connections: List[Component]
    features: List[Feature]
    types: List[Type]
    states: List[State]
    functions: List[Function]
    limits: List[Limit]
