# `faebryk` & `fabll` 🐍

`faebryk` is atopile's core. It's how we model the world.

`faebryk` is a Python module that uses a powerful and efficient core graph (nodes + edges) to represent every relationship in your design or circuit.

`fabll` is a Python framework to model circuits, much like `ato`. It unlocks a the whole Turing-complete power of Python to do design in + low-level procedural code and logic. Think of it like writing C for a Python module. It's focus is power - not ease of use like `ato`, so it's not recommended for most designs to start with.

!!! warning
    `fabll` is currently in a very early stage of development. It's not publicly supported yet.

## Building `fabll` code

To build a `fabll` module with atopile, you just need to point to the module within your `ato.yaml` configuration file.

When you run `ato build`, atopile will automatically build the `fabll` module and link it to your project.

## Importing `fabll` code

You can just import `fabll` modules in `ato` like any other import:

```ato
from path/to/some/fabll.py import SomeModule
```
