import datamodel as ato
import visualizer
import BME280
import ESP32
import PSU

# create a PSU component
psu = PSU.PSU

# create a ESP32 component
esp32 = ESP32.ESP32

# create a BME280 component
bme280 = BME280.BME280

#create another BME280 component
bme280_2 = BME280.BME280

# connect output of PSU to input of ESP32
ato.connect(esp32.power, psu.power_out)

# connect output of ESP32 to input of BME280
ato.connect(bme280.power, psu.power_out)

# connect ESP32 i2c to BME280 i2c
ato.connect(bme280.i2c, esp32.i2c)

# connect ESP32 i2c to BME280_2 i2c
ato.connect(bme280_2.i2c, esp32.i2c)

# connect BME280_2 power to PSU power_out
ato.connect(bme280_2.power, psu.power_out)

# visualize the circuit
components = [psu, esp32, bme280, bme280_2]
circuit_diagram = visualizer.visualize_circuit(components)
visualizer.save_drawio_xml(circuit_diagram, 'circuit_diagram.drawio')
