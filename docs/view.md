# atopile viewer

To use the viewer, start by building your project using:

``` sh
ato build
```

This will create a `<project-config>.view.json` file that the viewer can consume. Invoke the viewer using:

``` sh
ato view
```

The viewer will spool up a server on your local machine at [http://127.0.0.1:8080](http://127.0.0.1:8080). The viewer gets access to the `<project-config>.view.json` through http://127.0.0.1:8080/data.

## Viewer interface

### Navigate within your design

The left pane shows you the name of the instance you are currently viewing, the parent instance and provides two buttons: "return" gets you back to the parent module. "layout" recreates the default layout after you have moved blocks around.

To navigate within a module or component, simply click on it.

### Inspect links

Clicking on a link will show the source and target address that the link is connection. Those could either be two signals or two compatible instances of an interface.

## Features currently not supported (but planned)

- Saving the position of blocks
- Inspecting a links pin to pin connections
- Expanding and contracting modules (instead of navigating in and out of modules)
- A decent way to see components and their pins
- Ability to inspect multiple build configurations