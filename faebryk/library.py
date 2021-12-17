# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.libs.exceptions import FaebrykException
import logging
logger = logging.getLogger("library")

class Component:
    def __init__(self, name, pins, real):
        self.comp = {
            "name": name,
            "properties": {
            },
            "real": real,
            "neighbors": {pin: [] for pin in pins}
        }
        self.pins = pins

    def connect(self, spin, other, dpin=None):
        if dpin is None:
            if other.pins != [1]:
                raise FaebrykException
            dpin = 1
        if dpin not in other.pins:
            raise FaebrykException

        logger.debug("Connecting {}:{} -> {}:{}".format(
            self.comp["name"],
            spin,
            other.comp["name"],
            dpin
        ))
        self.comp["neighbors"][spin].append({
            "vertex": other.get_comp(),
            "pin": dpin,
        })

    def connect_zip(self, other):
        for pin in self.comp["neighbors"]:
           self.connect(pin, other, pin)

    def get_comp(self):
        return self.comp

class VirtualComponent(Component):
    def __init__(self, name, pins):
        super().__init__(name, pins, real=False)

# TODO experiment with multi inheritance
#   maybe real component for example should not inherit
#   from component but just add the constructor: footprint,value
class RealComponent(Component):
    def __init__(self, name, value, footprint, pins):
        super().__init__(name, pins, real=True)
        self.comp["value"] = value
        self.comp["properties"]["footprint"] = footprint

class ActiveComponent(RealComponent):
    def __init__(self, name, value, footprint, pwr_pins, pins):
        self.pwr_pins = pwr_pins
        for i in pwr_pins:
            if i not in pins:
                raise FaebrykException
        super().__init__(name, value, footprint, pins)

    def connect_gnd(self, gnd):
        self.connect(self.pwr_pins[0], gnd)

    def connect_vcc(self, vcc):
        self.connect(self.pwr_pins[1], vcc)

    def connect_power(self, vcc, gnd):
        self.connect_vcc(vcc)
        self.connect_gnd(gnd)

class Resistor(RealComponent):
    def __init__(self, name, value, footprint):
        super().__init__(
            name="R{}".format(name),
            value=value,
            footprint=footprint,
            pins=[1,2],
        )

class SMD_Resistor(Resistor):
    def __init__(self, name, value, footprint_subtype):
        super().__init__(name, value, "Resistor_SMD:{}".format(footprint_subtype))



class NAND(Component):
    def __init__(self, type, name, real):
        super().__init__(name, pins=[1,2,3,4,5], real=real)
        if real:
            raise NotImplementedError
            #self.comp["value"] = value
            #self.comp["properties"]["footprint"] = footprint

    def connect_in1(self, in1, dpin=None):
        self.connect(3, in1, dpin=dpin)

    def connect_in2(self, in2, dpin=None):
        self.connect(4, in2, dpin=dpin)

    def connect_out(self, out, dpin=None):
        self.connect(5, out, dpin=dpin)

class CD4011(ActiveComponent):
    def __init__(self, name, footprint):
        super().__init__(name, "CD4011", footprint, pwr_pins=[7,14], pins=range(1,14+1))
        self.nands = [NAND(type="4011", name=f"N{x}", real=False) for x in range(4)]

        for n in self.nands:
            n.connect(1, self, 14) #VDD
            n.connect(2, self, 7) #GND

        self.nands[0].connect_in1(self, 1)
        self.nands[0].connect_in2(self, 2)
        self.nands[0].connect_out(self, 3)

        self.nands[1].connect_in1(self, 4)
        self.nands[1].connect_in2(self, 5)
        self.nands[1].connect_out(self, 6)

        self.nands[2].connect_in1(self, 12)
        self.nands[2].connect_in2(self, 13)
        self.nands[2].connect_out(self, 11)

        self.nands[3].connect_in1(self, 8)
        self.nands[3].connect_in2(self, 9)
        self.nands[3].connect_out(self, 10)

