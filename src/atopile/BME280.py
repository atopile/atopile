from datamodel import Component, Pin, Feature

sda = Pin("sda", ref="7")
scl = Pin("scl", ref="8")
vcc = Pin("vcc", ref="1")
gnd = Pin("gnd", ref="2")

i2c_bme = Feature(name="i2c", pins=[sda, scl])
power_bme = Feature(name="power", pins=[vcc, gnd])

BME280 = Component(name="BME280", features=[i2c_bme, power_bme])
