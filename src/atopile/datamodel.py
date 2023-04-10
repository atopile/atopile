# TODO: should we make multiple "pins" for a single physical pin?
# eg. there's the pin (pin 3 say on the package), there's the pin
# that's jtag and there's the pin that's i2c, even though they're
# all on the same net

# TODO: we need to be able to define nets

from attrs import define
from typing import List

@define
class Pin:
    name: str

@define
class ConcretePin(Pin):
    ref: str

@define
class TransferFunction:
    eqn: str

@define
class Limit:
    eqn: str

@define
class Type:
    name: str
    pin: Pin

@define
class State:
    name: str
    transfer_functions: List[TransferFunction]
    limits: List[Limit]
    type: Type

@define
class Argument:
    name: str
    unit: str

@define
class BaseConfigurable:
    args: List[Argument]

@define
class Feature(BaseConfigurable):
    name: str
    pins: List[Pin]
    transfer_functions: List[TransferFunction]
    limits: List[Limit]
    states: List[State]  # states are always concrete

@define
class ConcreteFeature(Feature):
    pins: List[ConcretePin]
    types: List[Type]

@define
class Component(BaseConfigurable):
    name: str
    pins: List[ConcretePin]
    transfer_functions: List[TransferFunction]
    types: List[Type]
    limits: List[Limit]
    states: List[State]

    # all available features for this component
    features: List[ConcreteFeature]

@define
class ConcreteComponent(Component):
    component: Component
    features: List[ConcreteFeature] # enabled features

@define
class Net:
    name: str
    pins: List[Pin]
