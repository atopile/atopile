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
    pin: Pin

@define
class State:
    transfer_functions: List[TransferFunction]
    limits: List[Limit]
    type: Type

@define
class Feature:
    pins: List[Pin]
    transfer_functions: List[TransferFunction]
    limits: List[Limit]
    states: List[State]  # states are always concrete

@define
class ConcreteFeature(Feature):
    pins: List[ConcretePin]
    types: List[Type]

@define
class Component:
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

example = """
    feature i2c(Vsupply):
        pin gnd
        pin sda
        pin scl

        type[sda] = new type(sda)
        type[scl] = new type(scl)

        state on:
            V[sda:gnd] = (Vsupply/2 to Vsupply) + I[sda:gnd] * 0.1kR
            V[sda:gnd] = (Vsupply/2 to Vsupply) + I[scl:gnd] * 0.1kR

    component:
        pin vcc: 1
        pin gnd: 2

        feature i2c() from i2c(Vsupply=V[vcc:gnd]):2
            pin gnd: gnd
            pin sda: 3
            pin scl: 4
"""
# skidl notes:
# bad:
# - the way components are defined and imported sucks. There's a lack of links between the footprint, schematic, symbol, spice model etc...
# - the layout should be well linked to original source, so that changes propagate well without having to redo your entire layout
# - it's too easy to make mistakes in the schmematic and not be able to see them
# - there's no good way to visualise the circuits you're designing
# - connecting a pin at a time sucks, we want busses (I know skidl has them, but 🤷‍♂️)
# - it quickly becomes unclear what's connected to what
# - unconnected components shouldn't be part of a circuit by default
# good:
# - it was intuative to use - pythony, almost english descriptive
# - word operators are nice
# - liked being able to configure modules
