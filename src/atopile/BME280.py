from datamodel import Component, Pin, Feature

sda_bme = Pin("sda", ref="7")
scl_bme = Pin("scl", ref="8")
vcc_bme = Pin("vcc", ref="1")
gnd_bme = Pin("gnd", ref="2")

i2c_bme = Feature(name="i2c", pins=[sda_bme, scl_bme])
power_bme = Feature(name="power", pins=[vcc_bme, gnd_bme])

BME280 = Component(name="BME280", features=[i2c_bme, power_bme])
