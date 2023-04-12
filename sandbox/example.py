import datamodel as ato
import visualizer

from BME280 import BME280 as gas_sensor
from ESP32 import ESP32 as microcontroller
from PSU import PSU

# create a PSU component
psu = PSU

# create a ESP32 component
micro = microcontroller

# create a BME280 component
sensor = gas_sensor

# connect output of PSU to input of ESP32
ato.connect(micro.power, psu.power_out)

# connect output of ESP32 to input of BME280
ato.connect(sensor.power, psu.power_out)

# connect ESP32 i2c to BME280 i2c
ato.connect(sensor.i2c, micro.i2c)

# visualize the circuit
components = [psu, micro, sensor]
circuit_diagram = visualizer.visualize_circuit(components)
visualizer.save_drawio_xml(circuit_diagram, 'circuit_diagram.drawio')

def generate_netlist(components):
    netlist = {}
    processed_connections = set()

    for component in components:
        for feature in component.features:
            for connection in feature.connections:
                connection_id = frozenset({id(feature), id(connection)})
                if connection_id not in processed_connections:
                    processed_connections.add(connection_id)

                    for pin1, pin2 in zip(feature.pins, connection.pins):
                        net_name = pin1.name
                        if net_name not in netlist:
                            netlist[net_name] = []

                        netlist[net_name].append({"parent": component.name, "pin": pin1.ref})
                        netlist[net_name].append({"parent": connection._parent.name, "pin": pin2.ref})
    return netlist

# Example usage
components = [psu, micro, sensor]
netlist = generate_netlist(components)


# musings:
# you should only need to define features and their connections. 
# As soon as you start to think about your design with physical pins you break fungability.
# Rules and requirements will dictate your physical implication, NOT your cirucit description. 
# As you add features, available features will be shown, but features no longer available due to lack of pins will be hidden.
# features should have dependence on other features, eg. if you are using i2c feature, power feature is a requirement etc.
# order that you connect features doesnt matter
# features have rules that are checked when they are connected
# eg. if you connect a feature that has a max voltage of 3.3v to a feature that has a max voltage of 5v, you get an error.
# features could be common to multiple components, eg. i2c, power, etc, you could potentially swap a microcontroller with a 
# different one and it would still work if both had overlapping feature sets.
# types are defined for features, eg. i2c, power, etc to standardize a commonly used feature such that it can be interchangable between components,
# even if they have very different pinouts and physical implementations.
# types should be treated like string,int,bool etc, you can mess with them, but it is not standard to do so.
# features could be split across multiple components or combined into a single one - cool way to understand options to build custom silicon or optimize 
# for cost, number of components etc.
# it is super important that features are common and dont have to be uniquely defined.
# code should be generated from the circuit description, features should have linked library code.
# how should an analog signal be tracked through the circuit?
# uniqueness of circuts needs to be captured, maybe a JSON format or something like that. Generally speaking though, components are fungible and be treated as so.
# design your hvc before choosing BMB comms, should be able to swap it in and out super easily.

# Define block diagrams: Start by defining the high-level block diagrams of the system using code, as shown in the previous examples. 
# This provides a clear overview of the different components and their connections.
# Flesh out layers of depth: Engineers work on each block independently, adding more details, functionality, and complexity as required.
# This can be done in parallel by different teams or individuals, ensuring efficient use of resources and time.
# Validation: Validate each block and its functionality in isolation, using simulations, testing frameworks, and prototyping. 
# This helps identify and fix issues early in the development process.
# Integration: Integrate the blocks together and validate the system as a whole. 
# This step ensures that the individual components work together seamlessly.
# Iterate: Continuously iterate on the design, making changes and improvements at any level as needed. 
# This can involve updating specifications, adding new features, or addressing issues discovered during validation.
# Abstraction: Engineers working on specific parts of the system, such as interfacing with a camera driver, 
# do so in a way that is independent of the hardware implementation. This is achieved by using abstraction layers and interfaces, 
# allowing for easy swapping of components without the need to rewrite large parts of the code.
# Hardware flexibility: The system's modular design enables flexibility in hardware choices, making it possible to swap out components (such as microcontrollers) 
# with minimal impact on the overall project. This is particularly useful when dealing with supply chain issues or last-minute design changes.
# given a list of required features there is an optimal solution to capture those in a circuit.
# eg. if you need 3.3v, 5v, i2c, spi, uart, gpio, adc, dac, pwm, etc, there is a set of components that can be used to capture those features.
# this can be solved programmatically, given a list of required features, find the optimal solution to capture those features. 
# If features are properly defined, this should always give the best solution. 
# If you are unsure about the program being able to do that, you can add more information about your particular concern in the form of a constraint.
# contraints might be on enviromnent, voltage, current, timing, frequency etc. 
# ideally behaviour of components should be captured with sufficent fidelity to design a board such that in the future it will be the norm to
# be able to ship the board straight to production without any further valdiation or testing.
# this is a big ask, but it is possible.
