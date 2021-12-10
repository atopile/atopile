class FaebrykException(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)

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

class RealComponent(Component):
    def __init__(self, name, value, footprint, pins):
        super().__init__(name, pins, real=True)
        self.comp["value"] = value
        self.comp["properties"]["footprint"] = footprint

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

