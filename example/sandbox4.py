from atopile import net, Net, module, V, I, limit, assignment

@module
class SomeIC:
    def __init__(self):
        self.net('vcc')
        self.net('gnd')

    def i2c(self):
        self.net('sda')
        self.net('scl')

        self.assignment('V[sda:gnd] = (V[vcc:gnd] -> 0) + I[sda:gnd] * 0.1kR')
        self.limit('V[sda:gnd] < (V[vcc:gnd] -> 0) + I[sda:gnd] * 0.1kR')