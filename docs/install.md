# Packages and component installation

## Components

### Installing components from JLCPCB

Here is an example on how to install the [RP2040 chip](https://www.lcsc.com/product-detail/Microcontroller-Units-MCUs-MPUs-SOCs_Raspberry-Pi-RP2040_C2040.html) from [JLCPCB](https://jlcpcb.com/parts):

`ato install --jlcpcb C2040`

The command will add your footprint and 3D representation to the KiCAD library (named lib in your folder structure) and create an ato file of the component in the elec/src directory.

### Adding components manually

To manually add components, follow the instructions for creating a component in the type section.
<!--
TODO: link to the types
-->

## Packages

### Browsing packages

The [atopile package registry](https://packages.atopile.io) contains a list of existing ato packages. Packages usually contain components, module footprints, and layouts that can be reused in other projects.

A package usually points to a git repository that contains the design files, in a similar fashion to a standard atopile project.

See an example of a package with the [generics library](https://gitlab.atopile.io/packages/generics).

### Installing packages

To install a package, run the following command:

`ato install <your-package-name>`

The package will be added in the .ato/modules/your-package-name directory. It's installed just like existing git repositories that means you can make changes to it and push those changes back to the remote, if you have permissions to do so.

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
