from datamodel import Component, Pin, Feature, Limit

# BME280 pins
vdd = Pin("vdd", ref="1")
gnd = Pin("gnd", ref="2")
sda = Pin("sda", ref="3")
scl = Pin("scl", ref="4")
csb = Pin("csb", ref="5")
sdi = Pin("sdi", ref="6")
sck = Pin("sck", ref="7")
sdo = Pin("sdo", ref="8")

# BME280 features
i2c_feature = Feature(name="i2c", pins=[sda, scl])
i2c_feature.limits = [
    Limit(lambda sda_voltage: 1.2 <= sda_voltage <= 3.6),
    Limit(lambda scl_voltage: 1.2 <= scl_voltage <= 3.6)
]

spi_feature = Feature(name="spi", pins=[csb, sdi, sck, sdo])
spi_feature.limits = [
    Limit(lambda csb_voltage: 1.2 <= csb_voltage <= 3.6),
    Limit(lambda sdi_voltage: 1.2 <= sdi_voltage <= 3.6),
    Limit(lambda sck_voltage: 1.2 <= sck_voltage <= 3.6),
    Limit(lambda sdo_voltage: 1.2 <= sdo_voltage <= 3.6)
]

power_feature = Feature(name="power", pins=[vdd, gnd])
power_feature.limits = [
    Limit(lambda vdd_voltage: 1.71 <= vdd_voltage <= 3.6),
    Limit(lambda gnd_voltage: gnd_voltage == 0)
]

BME280 = Component(name="BME280", features=[i2c_feature, spi_feature, power_feature])
