from datamodel import Component, ConcretePin, ConcreteFeature

v_in = ConcretePin("v_in", ref="1")
v_out = ConcretePin("v_out", ref="2")
gnd_psu = ConcretePin("gnd", ref="3")

power_in = ConcreteFeature(name="power_in", pins=[v_in, gnd_psu])
power_out = ConcreteFeature(name="power_out", pins=[v_out, gnd_psu])

PSU = Component(name="PSU", features=[power_in, power_out])
