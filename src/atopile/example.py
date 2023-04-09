import datamodel
import visualizer

sda_esp = datamodel.ConcretePin("sda", ref="4")
scl_esp = datamodel.ConcretePin("scl", ref="5")
vcc_esp = datamodel.ConcretePin("vcc", ref="1")
gnd_esp = datamodel.ConcretePin("gnd", ref="6")

i2c_esp = datamodel.ConcreteFeature(
    name='i2c',
    pins=[sda_esp, scl_esp, gnd_esp],
    transfer_functions=[],
    limits=[],
    states=[],
    args=[],
    types=[]
)

#create a new component, ESP32, with the i2c feature
esp_power = datamodel.ConcreteFeature(
    name='power_in',
    pins=[vcc_esp, gnd_esp],
    transfer_functions=[],
    limits=[],
    states=[],
    args=[],
    types=[]
)
ESP32 = datamodel.Component(
    name='ESP32',
    pins=[],
    transfer_functions=[],
    types=[],
    limits=[],
    states=[],
    args=[],
    features=[i2c_esp, esp_power]
)

#create a new component, PSU (Power Supply Unit), with the v_in, v_out and gnd pins

v_in = datamodel.ConcretePin("v_in", ref="1")
v_out = datamodel.ConcretePin("v_out", ref="2")
gnd_psu = datamodel.ConcretePin("gnd", ref="3")

#create a power in feature
power_in = datamodel.ConcreteFeature(
    name='power_in',
    pins=[v_in, gnd_psu],
    transfer_functions=[],
    limits=[],
    states=[],
    args=[],
    types=[]
)

#create a power out feature
power_out = datamodel.ConcreteFeature(
    name='power_out',
    pins=[v_out, gnd_psu],
    transfer_functions=[],
    limits=[],
    states=[],
    args=[],
    types=[]
)

PSU = datamodel.Component(
    name='PSU',
    pins=[],
    transfer_functions=[],
    types=[],
    limits=[],
    states=[],
    args=[],
    features=[]
)

#create a new component, a BME280, with the i2c feature
sda_bme = datamodel.ConcretePin("sda", ref="7")
scl_bme = datamodel.ConcretePin("scl", ref="8")

i2c_bme = datamodel.ConcreteFeature(
    name='i2c',
    pins=[sda_bme, scl_bme],
    transfer_functions=[],
    limits=[],
    states=[],
    args=[],
    types=[]
)

vcc_bme = datamodel.ConcretePin("vcc", ref="1")
gnd_bme = datamodel.ConcretePin("gnd", ref="2")                                 
bme_power = datamodel.ConcreteFeature(
    name='power_in',
    pins=[vcc_bme, gnd_bme],
    transfer_functions=[],
    limits=[],
    states=[],
    args=[],
    types=[]
)

BME280 = datamodel.Component(
    name='BME280',
    pins=[],
    transfer_functions=[],
    types=[],
    limits=[],
    states=[],
    args=[],
    features=[i2c_bme, bme_power]
)

i2c = datamodel.FeatureNet(
    name='i2c',
    features = [ESP32.features["i2c"], BME280.features["i2c"]]
)

v3_3 = datamodel.FeatureNet(
    name='3v3',
    features = [ESP32.features["power_in"], BME280.features["power_in"], PSU.features["power_out"]]
)


features = [i2c, v3_3]
components = [ESP32, PSU, BME280]
circuit_diagram = visualizer.visualize_circuit(components, features)
visualizer.save_drawio_xml(circuit_diagram, 'circuit_diagram.drawio')









