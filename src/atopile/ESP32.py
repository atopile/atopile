from datamodel import Component, Pin, Feature

sda_esp = Pin("sda", ref="4")
scl_esp = Pin("scl", ref="5")
vcc_esp = Pin("vcc", ref="1")
gnd_esp = Pin("gnd", ref="6")

i2c_esp = Feature(name="i2c", pins=[sda_esp, scl_esp])
power_esp = Feature(name="power", pins=[vcc_esp, gnd_esp])

ESP32 = Component(name="ESP32", features=[i2c_esp, power_esp])
