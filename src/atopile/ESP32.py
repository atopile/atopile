from datamodel import Component, ConcretePin, ConcreteFeature

sda_esp = ConcretePin("sda", ref="4")
scl_esp = ConcretePin("scl", ref="5")
vcc_esp = ConcretePin("vcc", ref="1")
gnd_esp = ConcretePin("gnd", ref="6")

i2c_esp = ConcreteFeature(name="i2c", pins=[sda_esp, scl_esp])
power_esp = ConcreteFeature(name="power", pins=[vcc_esp, gnd_esp])

ESP32 = Component(name="ESP32", features=[i2c_esp, power_esp])
