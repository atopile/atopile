# Automatic selection of components

atopile provides a feature to select basic components automatically - at the moment for `Resistor`, `Capacitor` and `Inductor`. Component selection will happen automatically if your component is an instance of a class (or an instance of a subclass) of `Resistor`, `Capacitor` or `Inductor` from the generics library.

The fields that can be used for automatic selection are defined within the generics library. Generally speaking, you will want to set a value and a package to the components you wish to be selected. You are welcome to be more specific by specifying an operating temperature, a rated voltage, etc...

*If you set a `footprint` or an `mpn`, the selection won't happen*. See the reason below.

??? info "How does the compiler know which components to select?"
    We use the "[dunder](https://www.geeksforgeeks.org/dunder-magic-methods-python/)" `__type__ = "..."` parameter to figure out if a component should be selected or not. You will notice that this field contains `resistor` for the `Resistor` class, `capacitor` for the `Capacitor` class, etc... Adding a `__type__` dunder to other component class won't enable selection of other components though. We will add those manually in the future as we increase the scope of selection to other components.

## Package vs Footprint

In atopile, `package` defines the standardized shape of the component you wish to select. `footprint` refers to the specific file that will be located on your board layout. Typically, each component will have one unique footprint attached to it, even for components with similar packages. That's why you will want to define the package for the selection to operate and not the footprint.

## Lock files

Once a component is selected, we store information linked to the selection in the `ato-lock.yaml` file. This ensures that subsequent builds use the same component, wether they happen locally, in CI or on someone else's computer. Make sure you add the `ato-lock.yaml` file to your repo to enable this.

## Component selection API

We are in the process of updating the component API. We'll share docs once we have them.