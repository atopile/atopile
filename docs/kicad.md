# KiCAD layout

## KiCAD installation

To use atopile, you will need to install KiCAD. You can find it [on KiCAD's official website](https://www.kicad.org/download/)

## Import netlist into KiCAD

Follow this procedure to import a netlist into KiCAD:

1. File -> Import Netlist
![Import Netlist](assets/images/file-import.png)
1. Select the netlist you've just generated. The output is in the terminal, but it should approximately be servo-drive/build/servo-drive.net
2. Make sure you're using unique IDs, rather than designators (though they should work too)
3. Ruthlessly destroy stuff that's not supposed to be there (check boxes on the right)
![Import Netlist 2](assets/images/import-settings.png)
1. Check the errors - sometimes it's important

In case you want to setup your own project, we have prepared a template with sample `ato` code and KiCAD project. Find it [here](https://github.com/atopile/project-template).

!!! tip

    KiCAD needs to know where to look for the project's footprint. The `fp-lib-table` file points it to `build/footprints/footprints.pretty` which contains all the footprints. Make sure that is the case under preferences>manage footprint libraries. It should look like this:
    ![footprints](assets/images/footprints.png)