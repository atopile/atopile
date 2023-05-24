## High-level

Demonstrate a revision on a PCB
Show what CI looks like for hardware
 - add githash
Show what a PR looks like

## nitty gritty
(@matt) when you give a signal name, make sure that the net has the same name
    Gonna require some inteligence on which name takes precedence
when you stub something, it's assumed to be stubbed within the module it's defined
relatively positioned stubs
CI check versions of build used for netlist

collapsing modules in visualizer
(@matt) don't display stubs for signals within a module (mawildoer/tidy-stub-rendering)
symbols for stubs
labels should be inside blocks (components/modules)
symbols for blocks
improve compiler performance (see mawildoer/build-caching)
