# atopile viewer

To use the viewer, invoke the `ato view` cli command:

``` sh
ato view
```

If you have multiple build configuration, specify the one you would like to view with:

``` sh
ato view -b <your-build-config-name>
```

The viewer will spool up a server on your local machine at [http://127.0.0.1:8080](http://127.0.0.1:8080).

## Viewer interfaces

### Block diagram

![Block Diagram](assets/images/block_diagram_example.png)

The block diagram is meant to provide a view that resembles your code structure. In the block diagram view, you will see the same signals and interfaces that are present in your code as well as how they interact with each other. This view will help you navigate through your project and it's structure.

### Schematic

![Schematic](assets/images/schematic_example.png)

The schematic view follows a more standard view of your design. This view can be used for documentation or inspecting a more concrete view of your final circuit. The schematic view can be enabled by navigating with the block diagram to the block you want to inspect and pressing the schematic button. You can switch back to block diagram by pressing the same button.

The schematic diagram will represent all the components that are at the level or below the current module.

## Navigate within your design

To navigate within a module or component, simply click on it.
*return*: This button brings you back to the parent module
*re-layout*: This button re-lays out the modules for you
*schematic/block diagram*: Switch between the two viewing modes
*reload*: Loads the latest changes for your code. This feature hasn't been enabled from the block diagram yet.

### Inspect links

Clicking on a link in the block diagram will show the source and target address that the link is connection. Those could either be two signals or two compatible instances of an interface.

## Features currently not supported (but planned)

- Saving the position of blocks and components
- Inspecting a links pin to pin connections
- Expanding and contracting modules (instead of navigating in and out of modules)
- A decent way to see components and their pins