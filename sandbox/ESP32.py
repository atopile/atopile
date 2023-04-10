from datamodel import Component, Pin, Feature

sda = Pin("sda", ref="4")
scl = Pin("scl", ref="5")
vcc = Pin("vcc", ref="1")
gnd = Pin("gnd", ref="6")

i2c = Feature(name="i2c", pins=[sda, scl])
power = Feature(name="power", pins=[vcc, gnd])

ESP32 = Component(name="ESP32", features=[i2c, power])
