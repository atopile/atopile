# TODO: should we make multiple "pins" for a single physical pin?
# eg. there's the pin (pin 3 say on the package), there's the pin
# that's jtag and there's the pin that's i2c, even though they're
# all on the same net

# TODO: we need to be able to define nets

from attrs import define
import attr
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
    # args: List[Argument]
    pass

@define
class Feature(BaseConfigurable):
    name: str
    pins: List[Pin]
    # transfer_functions: List[TransferFunction]
    # limits: List[Limit]
    # states: List[State]  # states are always concrete

@define
class ConcreteFeature(Feature):
    pins: List[ConcretePin]
    _parent: 'Component' = None
    connections: List['ConcreteFeature'] = attr.field(factory=list)
    # types: List[Type]

@attr.define
class Component:
    name: str
    features: List[ConcreteFeature] = attr.field(factory=list)

    def __attrs_post_init__(self):
        for feature in self.features:
            feature._parent = self

    def __getattr__(self, name):
        for feature in self.features:
            if feature.name == name:
                return feature
        raise AttributeError(f"{self.__class__.__name__} object has no attribute {name}")




@define
class ConcreteComponent(Component):
    component: Component
    features: List[ConcreteFeature] # enabled features

@define
class Net:
    name: str
    pins: List[Pin]

@define
class FeatureNet(list):
    pass

def connect(feature1: ConcreteFeature, feature2: ConcreteFeature):
    feature1.connections.append(feature2)
    feature2.connections.append(feature1)