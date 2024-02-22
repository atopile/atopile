# Units and tolerances

## Units

Remember how NASA slung a rocket straight into Mars because of a metric/imperial boo boo?

How about we don't do that again.

Resistors's resistances must be a resistance; whether `1.23Ω` (option+Z on OSx), `1.23ohm`, `4.56Kohm`, `7.89Mohm` or similar.

Any attribute of any block may have a unit attached written (without a space) after any number.

Unsurprisingly, caps capacitances need to be a capacitance; eg. `23.4uF`, various limits in volts, amperes, degrees and so on.

Add units.

## Tolerances

Another unfamiliar first-class language feature when dealing with the physical world is the ability (and generally requirement)
to spec tolerances for attributes.

You could try find a `10kΩ` resistor, but my money says you won't - it'll likely be at least `10kΩ +/- 0.1%` (which you can
write!)

Tolerances can be written in the forms of:
- `1V to 2V`
- `3uF +/- 1uF`
- `4Kohm +/- 1%`

These are hopefully sufficiently intuitive as to not warrant further explanation 🤞


## Units and Tolerances

With Units and Tolerances together, we can define Physical attributes.

There's quite a few legal ways to combine them!

- `3V to 3.6V` perhaps for a supply rail
- `3V +/- 10mV` maybe for a reference
- `4.7uF +/- 20%` for a generic cap
- even `25lb +/- 200g` 🤣