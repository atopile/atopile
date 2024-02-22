# Install dependencies

## Components

### Installing components from JLCPCB

Here is an example on how to install the [RP2040 chip](https://www.lcsc.com/product-detail/Microcontroller-Units-MCUs-MPUs-SOCs_Raspberry-Pi-RP2040_C2040.html) from [JLCPCB](https://jlcpcb.com/parts):

`ato install --jlcpcb C2040`

The command will add your footprint and 3D representation to the KiCAD library (named lib in your folder structure) and create an ato file of the component in the elec/src directory.

### Adding components manually

To manually add components, follow the instructions for creating a component or footprint in the section below.
<!--
TODO: link to the types
-->

## Packages

### Browsing packages

The [atopile package registry](https://packages.atopile.io) contains a list of existing ato packages. Packages usually contain components, module footprints, and layouts that can be reused in other projects.

A package usually points to a git repository that contains the design files, in a similar fashion to a standard atopile project.

See an example of a package with the [generics library](https://gitlab.atopile.io/packages/generics).

### Installing packages

### Install - from the package manager <small>recommended</small>

To install a [package](https://packages.atopile.io), run the following command:

`ato install <your-package-name>`

The package will be added in the .ato/modules/your-package-name directory. It's installed just like existing git repositories that means you can make changes to it and push those changes back to the remote, if you have permissions to do so.

### Install - from a git repo

To install a package from a git repository, run the following command:

`ato install <your-repository-url>`

The package will be added will be added to your dependencies in a similar fashion than the procedure above. See below for the procedure to specify a specific package.

### Upgrading packages & version management

You can pull the latest packages by running:

`ato install --upgrade`

This will pull the latest tag version for the packages. If you wish to further specify which version of the package you'd like to install, you can use semantic versioning in the `ato.yaml` file. For example, you can request the highest available version of the generics package 1.x.x:

!!! file "ato.yml"
    ```yaml
    ...
    dependencies:
    - generics^v1.0.0
    ```

!!! tip
    The compiler version follows [sementic versioning](https://semver.org). The required version of your dependencies can be specified using [npm's standard](https://docs.npmjs.com/about-semantic-versioning).

### Adding packages

The top of the [atopile package registry](https://packages.atopile.io) contains a form to add packages. Add the name and the link to the git repository (GitLab or GitHub for example) and click submit. Your package should now be available to the community!


## Adding custom footprints

In cases where you can't find the footprint that you'd want to use on [JLCPCB](https://jlcpcb.com/parts) or in the [atopile package registry](https://packages.atopile.io), you can also add it manually. KiCAD has a library of footprints you can use [on GitLab](https://gitlab.com/kicad/libraries/kicad-footprints) (those should be installed locally already if you opt-in to install the default library when installing KiCAD, which we recommend you do). From there, you have two options:

**Add the footprint to your ato project**

If you have a footprint selected, you can move it to your `atopile` project in the `elec/footprints/footprint.pretty` directory.
From your component, you can point to that footprint. You also need to connect the footprint pads to signals that you will use throughout your project. For example, if the footprint is called `my_footprint.kicad_mod` and the pads `PAD1` and `PAD2`:

```python
component MyComponent:
    footprint = "my_footprint"
    signal in ~ pin PAD1
    signal out ~ pin PAD2
```

**Use footprints from the kicad default library**

The procedure would be the same as the one outlined above except that you don't have to add the footprint to the atopile `elec/footprints/footprint.pretty` directory. KiCAD will find it in it's own default library. This will only work if the KiCAD has the default library installed.


??? question "How to inspect your footprints?"

    To inspect a footprint, you can use KiCAD's footprint editor

    ![KiCAD footprint editor](https://github.com/atopile/atopile/assets/9785003/1f9176c9-76a6-4fdb-8e18-8f6b0c212a0d)

    You can also inspect the file itself and find the pads. Here is what they look like:
    `(pad "1" smd roundrect (at -0.48 0) (size 0.56 0.62) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25) (tstamp f0d6bdbe-8dea-4984-9c52-f76168ceed26))`

??? question "How to draw new footprints that aren't in existing libraries?"

    KiCAD provides documentation on how to draw custom footprints [here](https://docs.kicad.org/7.0/en/getting_started_in_kicad/getting_started_in_kicad.html#creating_new_footprints).