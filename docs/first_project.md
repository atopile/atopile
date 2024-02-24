# Creating an ato project

## Project structure setup

### With `ato create` <small>recommended</small>

To create a project, you can run the command

```
ato create
```

This command will start by asking for a name to your project. It will then clone the [project template](https://github.com/atopile/project-template) on github. Once created on GitHub, paste your repository URL into the command line. Your project should be up and running!

We also added a firmware and mech folder to store 3D designs or firmware associated with your project. Version controlling everything under the same project can be quite handy.

### Manually

You can create your own project instead of using ato create. Perhaps you will want to setup the project and for it as you create your ato projects. Make sure to follow this project structure:

```{ .no-copy }
.
├── venv -> (active) virtual environment with python^3.11 and atopile installed
└── your-project
    ├── ato.yaml --> definition file for your atopile project
    ├── elec --> your virtual environment
    │    ├── src
    │    │   └── file.ato
    │    └── layout
    │        └── default
    │            ├── kicad-project.kicad_pro
    │            ├── kicad-project.kicad_pcb
    │            ├── kicad-project.kicad_sch
    │            └── fp-lib-table
    └── ci/cd file --> useful for running jobs automatically on your repo
```

!!! tip

    Our [template project](https://github.com/atopile/project-template/tree/main) contains example code for a github CI workflow to compile your ato files and access your manufacturing files from kicad. Find it [here](https://github.com/atopile/project-template/blob/main/.github/workflows/ci.yml).

## `ato.yaml` setup

The root of an ato project is marked by the presence of an `ato.yaml` file.

`ato.yaml` contains some project configuration information like the list of things you want to build. It's similar in concept to a package.json in js/node/npm land.

Here's an example:

```yaml
# this line defines the version of compiler required to compile the project
ato-version: ^0.0.18
# those lines define the elements that will be built by the compiler
builds:
  default:
    entry: elec/src/your-project.ato:YourProject
# The compiler version follows semantic versioning. The required version to compile your project can be specified using npm's standard.

# Those lines define the package dependencies that your project might have. You can specify the exact package version you want using semantic versioning.
dependencies:
- generics^v1.0.0
```

!!! tip
    The compiler version follows [sementic versioning](https://semver.org). The required version to compile your project can be specified using [npm's standard](https://docs.npmjs.com/about-semantic-versioning). The same applies to your dependencies.

## Building the project

To test that your project is building, run:

`ato build`

!!! tip

    `ato build` will build the default module and kicad layout. You can specify a specific target with:

    `ato build --build [name_of_your_build]`

    The build name is defined in the `ato.yaml` file.

You should see a build directory appear in your project structure. This is where atopile places the output files generated from compilation.

<!---
TODO: what should the user expect to see
-->
