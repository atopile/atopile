---
date: 2024-01-31
authors: [narayan]
description: >
  Automatic component selection!
categories:
  - Release
links:
---

# Cloud Components

I am pretty excited about this one. In our latest release 0.2.5, we are introducing 'Cloud Components' - a way to parametrically define and select components from a server.

## How it works
First step is defining the requirements of the component, much like you would in a digikey search. Currently our library has support for resistors, capacitors, inductors, diodes, and FETs. Here's an example of how you would define a few components:
```ato
resistor = new Resistor
resistor.value = 10kohm +/- 20%
resistor.package = "0603"

cap = new Capacitor
cap.value = 1uF +/- 10%
cap.package = "0603"

fet = new NFET
fet.current_a = 30A to 100A
fet.drain_source_voltage_v = 30V to 100V

inductor = new Inductor
inductor.inductance = 1uH to 10uH
inductor.current = 3A to 5A

diode = new Diode
diode.forward_voltage = 7V to 9V
diode.impedance = 1ohm to 10ohm
diode.power_dissipation = 5W to 60W
```
At build time, we take the requirements and send them to our component server, which filters parts in our library for the specified requirements. The server then sorts the parts by price and availability, and returns the best matches. These components are then downloaded and added to your BOM and netlist.

![BOM output](/assets/images/cloud_bom.png)

### Footprints
This was a bit of a pain. This is pretty simple for things like resistors and caps, but becomes a little more complex for devices like mosfets that might have three pins on some parts and eight on others. Our current solution, which admittedly is a bit of a hack, stores a muated footprint in the server for each part, downloads it and adds it to your library.

For example, here is a multi-pin mosfet, you can see that the pin names have been mutated to their corresponding signals:

<img src="/assets/images/mosfet.png" alt="Example Image" width="200">

## Why this is a big deal
The way circuits are defined today requires us as designers to be explicit as to which part number each component will have, in the process loosing information about why you chose that component. If a design at your company has a component shortage and you are assigned the task to find a replacement, how do you know which part to choose, what are the requirements? If you are luck there might be a design document or confluence page you can scroll through to reverse engineer the design and check new parts against it. If you are unlucky, the guy who designed it left the company and only took paper notes.

By capturing the requirements in your source code, the information is preserved and can be used even years later to find a suitable part. I imagine a future where automated systems can track component pricing and inventory, automatically finding cost down opportunities, or alerting you when a part is going end of life and proposing a replacement.

More immediately, as a designer making a quick turn board, I don't want to spend time browsing digikey, seeing what is available, checking if we have it in our companies component library, only to hear back from the vendor that the component is now out of stock and they need me to pick a new one. Thats enough to make a grown man cry, some days. Instead, we can have the tool generate a list of alternatives that meet the requirements and allow the vendor to pick from that list.

## What is next?
I believe that a fundamental transformation of how we capture circuit information is needed to enable the next generation of tools. In order to make our tools truly smart, we need to come up with ways to communicate design intent, not just one explicit implementation.
Concretely, we are working on:

- Adding more component types to the server
- Adding support for project level requirements and constraints: AECQ100, Environmental conditions, etc
- Component traits - how to generically describe complex components (blog post coming soon)

Stay tuned for more updates!

Narayan