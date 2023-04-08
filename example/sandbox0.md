# ato language spec, take 2

what if there were abstract mathematic symbols to represent protocol instances?

eg. `V[scl:gnd] = V[vcc:gnd] * i2c.scl` where `i2c.scl` is a protocol

drive strength is a function relating V and I:

```
pinx = (io1, io2, io3)  # not sure how much I like this yet, but gist is that when used, this expands, equivalent to for pinx in ...
V[*pinx:gnd] = (0V to V[vcc:gnd]) + 10kR * I[*pinx]  # convention of current into a device
```

what about capacitance and inductance?

```
C[pinx:gnd] = 1nF
L[pinx:gnd] = 1nH
```

and some limits:
```
C[pinx:gnd] < 1nF
L[pinx:gnd] < 1nH
```

# more extended example

## notes:

- I guess this makes protocol basiaclly just a "copper" component. They basically function the same, it's just that you need to implement protocols physically as traces, while components are, well, components.

```
protocol i2c:
    signals:
        sda
        scl

    wires:
        sda
        scl
        gnd

    C[:] < 1nF

    -0.ps < T[sda] - T[scl] < 0.ps

    # how do you specify that all the connections to sda, scl must be equal?
    # it can be taken from the assumption of equality between pins' voltages
    # eg.:
    -0.3V < V[scl:gnd] * signals.scl < 0.3V

    # specifically in this case how do you specify how close each of the pins must be to one
    # can we use an inequality directly on the signal vector instead?
    -0.3V < signals.scl < 0.3V

    # this implies the signal vector isn't global, rather an instance of vector of indeterminate magnitude in a common direction
    # the above should really be more specific:
    -0.3V < max_delta[signals.scl] < 0.3V

    direction(V[scl:gnd]) == signals.scl
    direction(V[scl:gnd]) == on
    direction(V[scl:gnd]) == off


class SomeIC:
    symbol = ...
    footprint = ...

    wires:
        vcc: 1
        gnd: 2

    C[vcc:gnd] > 10uF
    L[vcc:gnd] < 1nH

    feature i2c:
        wires:
            sda: 3
            scl: 4
            gnd: self.gnd

        V[scl:gnd] -> V[vcc:gnd] * i2c.signals.scl
        V[sda:gnd] -> V[vcc:gnd] * i2c.signals.sda

ic_a = SomeIC(i2c())
ic_b = SomeIC(i2c())

ic_a.i2c ~ ic_b.i2c

# from here on out I'm manually doing what I imagine the compiler is doing
V[ic_a.:gnd]

```

We're referring to a couple of things with somewhat interchangable names:

- wires / nets
- protocols / signals
- interfaces on ICs; eg. ic_a.i2c.sda and ic_b.i2c.sda aren't the same thing, and are driven differently





1. protocol type propgates along copper
2. if there's something on the bus that has a protocol, it'll throw an error if there's something else on the bus that doesn't have the same protocol/no protocol





```

class SomeIC:
    wires:
        vcc: 1
        gnd: 2

    rules:
        -0.5V < V[vcc:gnd] < 3.8V

    feature i2c:
        wires:
            sda: 3
            scl: 4
            gnd: gnd

        rules:
            Voff <= 0.3V
            Von >= 2.0V
            Voff > -0.5V
            Von <= 3.3V

        behaviour:
            Von = 2.5V
            Voff = 0.0V
            I < 10mA

```
class SomeIC:
    symbol = ...
    footprint = ...

    wires:
        vcc: 1
        gnd: 2

    C[vcc:gnd] > 10uF
    L[vcc:gnd] < 1nH

    feature i2c:
        wires:
            sda: 3
            scl: 4
            gnd: self.gnd

        V[scl:gnd] = V[vcc:gnd] * i2c.signals.scl
        V[sda:gnd] = V[vcc:gnd] * i2c.signals.sda
```

```
class amp:
    wires:
        in_p: 1
        in_n: 2
        out: 3
        gnd: 4
        vcc: 5

    3.15V > V[vcc:gnd] > 50V
    -V[vcc:gnd] - 0.1V > V[in_p:gnd] > 70V - V[vcc:gnd]
    -V[vcc:gnd] - 0.1V > V[in_n:gnd] > 70V - V[vcc:gnd]

    I[vcc:gnd] -> normal(1.5mA, 0.2mA)

    V[out:gnd] = {
        0 if V[in_p:gnd] <= V[in_n:gnd] + (-40uV to 40uV),
        (V[in_p:gnd] - V[in_n:gnd]) * 120dB,
        V[vcc:gnd] if V[in_p:gnd] >= V[in_n:gnd] + (-40uV to 40uV),
    }
```
