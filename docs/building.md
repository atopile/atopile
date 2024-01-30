# Building your ato project

## Building predefined entry points

The `ato.yaml` file can contain predefined build configurations. Those can be defined like so:

!!! file "ato.yml"
    ```yaml
    ...
    builds:
        default:
            entry: elec/src/your-project.ato:YourModule
        build-2:
            entry: elec/src/your-second-project.ato:YourSecondModule
    ...
    ```
The `ato build` command will build the atopile modules for all of those entry points.

For a specific build, you can use the -b or --build option like so:
```
ato build -b build-name
```
or
```
ato build --build build-name
```

## Building a given entry point

A given entry point can be built like so from your atopile project directory:

```
ato build elec/src/your-project.ato:YourModule
```

## Building given targets

Those are the targets that can currently be built by atopile:

- Netlist ("netlist")
- Bill Of Material ("bom")
- Designator Map ("designator-map")
- Manufacturing Data ("mfg-data")
- Consolidate footprint ("copy-footprints")
- All of the above ("all")

The target can be specified with the `-t` or `--target` like so:

```
ato build -t target-name
```
or
```
ato build --target target-name
```