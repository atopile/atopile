from datamodel import Component, Pin, Feature

v_in = Pin("v_in", ref="1")
vcc = Pin("vcc", ref="2")
gnd = Pin("gnd", ref="3")

power_in = Feature(name="power_in", pins=[v_in, gnd])
power_out = Feature(name="power_out", pins=[vcc, gnd])

PSU = Component(name="PSU", features=[power_in, power_out])
