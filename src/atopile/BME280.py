from datamodel import Component, ConcretePin, ConcreteFeature

sda_bme = ConcretePin("sda", ref="7")
scl_bme = ConcretePin("scl", ref="8")
vcc_bme = ConcretePin("vcc", ref="1")
gnd_bme = ConcretePin("gnd", ref="2")

i2c_bme = ConcreteFeature(name="i2c", pins=[sda_bme, scl_bme])
power_bme = ConcreteFeature(name="power", pins=[vcc_bme, gnd_bme])

BME280 = Component(name="BME280", features=[i2c_bme, power_bme])
