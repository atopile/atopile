# 5. Layout

`ato` code defines the function of the circuit via how everything is connected up. Unlike a software compiler, these components all need to end up placed somewhere and copper traces need to be routed between the elements for the circuit to function.

This process is typically called "layout".

atopile uses [KiCAD](https://kicad.org), the premier open-source electronics design package for layout.

## Opening KiCAD

When you run `ato build`, `ato` will generate a KiCAD project file for you.

The easiest way to open this is to add the `--open` flag to the `build` command:

```bash
ato build --open
```

This will open the KiCAD project file in a new window.

## KiCAD plugin

The `ato` compiler automatically installs a KiCAD plugin to help you with layout. This saves insane amounts of time, so we definitely recommend using it!

The plugin is installed automatically when you run the `ato` CLI, but in case something went wrong, you can re-trigger the installation by running `ato configure`.

## Start with existing modules

If you import the rp2040 module we installed in the [previous chapter](4-packages.md), you can reuse its layout.

```ato
from "rp2040/RP2040Kit.ato" import RP2040Kit

module App:
    uc = new RP2040Kit
    # Note: I've emptied this module out for brevity.
    # You can decide whether you want to keep the demo voltage divider or not.

```

To reuse a layout from a module:

- run an `ato build`, to make sure the layout is synced with the code
- hit the "Sync Group" button in the KiCAD plugin
- select the group you want to sync, and hit the "Pull" (Down arrow) button to pull the layout from the module's KiCAD layout file

<video autoplay loop muted playsinline>
    <source src="../assets/5-pcb-layout-sync.mp4" type="video/mp4">
    <img src="../assets/5-pcb-layout-sync.gif" alt="Animated fallback">
</video>

!!! info "Under the hood :wrench:"

    The `ato` compiler will map layouts with a **class or super-class** that **has a build**.

    The `RP2040Kit` in the example is the class, and the `ato.yaml` config file in the `rp2040` package means that there's a layout associated with it.

    If you want to create a reusable layout for a class of your own, the easiest way is to add a new build config with `ato create build`, and then point the newly created [entry](../reference/config.md#builds.entry) at the module you've made.

## Layout the remainder of your design

Use KiCAD to place-and-route the remainder of your design, just like if you got it from the schematic editor.

If you can't find the quality of KiCAD docs you need to get started, drop a comment or upvote on this Github Issue !882


## Auto-layout :rocket: ?881

atopile can do small bits of auto-layout for you, however it's not completely exposed to `ato` yet.

If this is a feature that'd super-charge your workflow, please come vote and discuss it in the Github Discussion ?881
