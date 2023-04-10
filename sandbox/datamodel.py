# TODO: should we make multiple "pins" for a single physical pin?
# eg. there's the pin (pin 3 say on the package), there's the pin
# that's jtag and there's the pin that's i2c, even though they're
# all on the same net

# TODO: we need to be able to define nets

from attrs import define
import attr
import uuid
from typing import List

@define
class Pin:
    name: str
    ref: str = None
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
class Feature:
    name: str
    pins: List[Pin]
    _parent: 'Component' = None
    connections: List['Feature'] = attr.field(factory=list)

@attr.define
class Component:
    name: str
    features: List[Feature] = attr.field(factory=list)
    id: str = attr.field(default=attr.Factory(lambda: str(uuid.uuid4())))

    def __attrs_post_init__(self):
        for feature in self.features:
            feature._parent = self

    def __getattr__(self, name):
        for feature in self.features:
            if feature.name == name:
                return feature
        raise AttributeError(f"{self.__class__.__name__} object has no attribute {name}")

def pins_match(feature1: Feature, feature2: Feature) -> bool:
    if len(feature1.pins) != len(feature2.pins):
        return False

    feature1_pins = sorted([pin.name for pin in feature1.pins])
    feature2_pins = sorted([pin.name for pin in feature2.pins])

    return feature1_pins == feature2_pins


def connect(feature1: Feature, feature2: Feature):
    if not pins_match(feature1, feature2):
        raise ValueError(f"Cannot connect {feature1._parent.name}.{feature1.name} and {feature2._parent.name}.{feature2.name}. Their pins do not match.")

    print(f"Connecting {feature1._parent.name}.{feature1.name} and {feature2._parent.name}.{feature2.name}.")
    # Pins for feature1 and feature2 are the same
    for pin in feature1.pins:
        print(f"Connecting {pin.name} on {feature1._parent.name}.{feature1.name} to {pin.name} on {feature2._parent.name}.{feature2.name}.")

    feature1.connections.append(feature2)
    feature2.connections.append(feature1)


