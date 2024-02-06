---
date: 2024-01-31
authors: [narayan]
description: >
  Building the right lego blocks: Composable electronics
categories:
  - Future
links:
---

# Composable Electronics

How do we make designing electronics more like playing with legos? We need to standardize the building blocks, how they can be connected together and publish 'instruction manuals' that describe how to connect them up to make something useful.

## The blocks
How do you describe what a component is? Today we rely on a language description in a datasheet and a clever human to interpret it. The information is not easily interpretable by a computer, which makes it hard to automate or augment the design process.

We need a way to embed key information into the source files.

### What are the functional blocks inside the chip?
Here is a simple example of a buck converter IC.
<img src="/assets/images/buck_ic.png" alt="Example Image" width="400">
Lets try simplify this into a few functional blocks. Lets say the 'controller' is a block that takes in a voltage outputs a switching node, with a feedback pin. We can just use a NFET component for the fet. So in ato code we could define this as:
```python
component LM2841:
    controller = new BuckController
    nfet = new NFET
```

### Connecting and configuring the blocks
To more completely describe the internals of the IC, we need to define how the blocks are connected and what their properties are. Below we are connecting the NFET to the controller, connecting the blocks to the outputs and configuring the voltage and current limits.
```python
# connect blocks to pins
controller.feedback ~ fb
controller.power_in.vcc ~ vin
controller.power_out.gnd ~ gnd
nfet.drain ~ sw
```
We will also need to add in any specifics required by this particular IC, like a bootstrap capacitor and a pull-up on the enable pin that ill leave out of this example.

## The Instruction Manual

Following through with our buck converter example, lets build a description of how to connect the blocks together to make a buck converter.
<img src="/assets/images/buck_topology.png" alt="Example Image" width="400">

To start, lets make a new 'topology' and instantiate the required blocks.
```python
topology Buck:
    # Define external interfaces
    power_in = new Power
    power_out = new Power

    # Define blocks
    inductor = new Inductor
    output_cap = new Capacitor
    input_cap = new Capacitor
    diode = new Diode
    controller = new BuckController
    nfet = new NFET
    feedback_divider = new VDiv

```

Next, lets connect the blocks together.
```python
    # Connect internal components
    controller.drive ~ nfet.gate
    # Method to chain dipole components (feedback welcome)
    power_in.vcc ~ nfet ~ inductor ~ power_out.vcc
    diode.anode ~ gnd
    diode.cathode ~ inductor.1

    # Feedback divider (input is a power interface)
    feedback_divider.input ~ power_out
    feedback_divider.output ~ controller.feedback


    # Connect bypass capacitors
    power_in ~ input_cap
    power_out ~ output_cap

    # We might want to define some equations to make the buck more intuitive to use
    eqn: power_out.voltage = feedback_divider.input.voltage
    eqn: controller.feedback.voltage = feedback_divider.output.voltage
```

Finally, we need a way to relate the two. Let now create a specific instance of the topology and define the parameters.
```python
buck = new Buck
ic = new LM2841

# Map the IC to the topology using the replacement operator
buck.controller -> ic.controller
buck.nfet -> ic.nfet

# Configure the buck components
buck.inductor.inductance = 10uH +/- 20%
input_cap.capacitance = 10uF +/- 20%
output_cap.capacitance = 10uF +/- 20%

# Configure output voltage
buck.power_out.voltage = 5V +/- 5%
```

That might all feel like alot of work, until you realize that the topologies and components are reusable and only need to be defined once. You can design a buck converter using just that last block of code and a few imports.

If you are interested in checking out the full example, you can find it [here](https://github.com/napowderly/traits-playground)

We have a few language features in the pipeline that will enable this type of workflow in the near future.

Narayan