from datamodel import Component, Pin, Feature

adc_1_pins = [
    Pin("adc_0", ref="VP"), 
    Pin("adc_3", ref="VN"), 
    Pin("adc_6", ref="34"), 
    Pin("adc_7", ref="35"),
    Pin("adc_4", ref="32")]

features = []
for pin in adc_1_pins:
    feature = Feature(name=pin.name, pins=[pin])
    feature.type = Feature.adc
    feature.bits = 12
    feature.sample_rate = 1000
    features.append(feature)

gpio_pins = [
    Pin("gpio_36", ref="VP"),
    Pin("gpio_39", ref="VN"),
    Pin("gpio_34", ref="34"),
    Pin("gpio_35", ref="35"),
    Pin("gpio_32", ref="32"),
    Pin("gpio_33", ref="33"),
    Pin("gpio_25", ref="25"),
    Pin("gpio_26", ref="26"),
    Pin("gpio_27", ref="27"),
    Pin("gpio_14", ref="14"),
    Pin("gpio_12", ref="12"),
    Pin("gpio_13", ref="13"),
    Pin("gpio_15", ref="15"),
    Pin("gpio_2", ref="2"),
    Pin("gpio_4", ref="4"),
    Pin("gpio_16", ref="RX"),
    Pin("gpio_17", ref="TX"),
    Pin("gpio_5", ref="5"),
    Pin("gpio_18", ref="18"),
    Pin("gpio_19", ref="19"),
    Pin("gpio_21", ref="21"),
    Pin("gpio_3", ref="RX0"),
    Pin("gpio_1", ref="TX0"),
    Pin("gpio_22", ref="22"),
    Pin("gpio_23", ref="23")
]   

for pin in gpio_pins:
    feature = Feature(name=pin.name, pins=[pin])
    feature.type = Feature.gpio
    features.append(feature)


# define i2c interface
# there are two interfaces, i2c0 and i2c1, each can use any of the gpio pins







ESP32 = Component(name="ESP32", features=features)
