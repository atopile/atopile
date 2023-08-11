# Getting Started

## Installing atopile

Currently `atopile` is only available from source.

Clone this repo `git clone https://gitlab.atopile.io/atopile/atopile.git`

`cd` to it

I strongly recommend sticking it in a virtual environment. You can create one with `python3 -m venv .venv`

Then activate this environment with `source .venv/bin/activate`

Install atopiole with `pip install -e ."[dev,test,docs]'`

## Syntax highlighting is pretty nice...

Copy `src/vscode_extension` to `~/.vscode/extensions/`
eg. `cp -r src/vscode_extension ~/.vscode/extensions/atopile-0.0.1`

## Creating a new project

The easiest way to create a new project at the moment is to clone from an example, eg. `git clone https://gitlab.atopile.io/atopile/servo-drive.git`

`cd elec/src` to get to the core of the atopile project in there.

## Making your first component

Create a new file `led.ato` with the following contents:

```ato
component LED:
    signal positive ~ pin 1
    signal negative ~ pin 2

```

## Basic project modifications

`ato.yaml` currently contains a bunch of junk (to you) related to the bike light project.

```yaml
builds:
  default:
    # we don't have a default root file yet
    targets:
      - netlist-kicad6
      - designators
      - bom-jlcpcb
```

## Viewing your first component

`ato view` is the tool for you!

`ato view --help` will give you a printout of the options it can take.

atopile paths are in the form `path/to/file.ato:module.within.file`

To view, the LED component for example: `ato view led.ato:LED`

You should get a browser window popping up and wham! bam! alakazam! you've got a component!

## Adding footprints to your project

[JLCPCB](https://jlcpcb.com/) is a great place to get cheap PCBs made. They have a [library](https://jlcpcb.com/parts) of footprints that you can use.

To pull in a footprint, we've been using the wonderful tool [easyeda2kicad](https://pypi.org/project/easyeda2kicad/).

Add it to your python environment with `pip install easyeda2kicad`

Then you can download JLCPCB/EasyEDA/LCSC footprints with `easyeda2kicad --full --lcsc_id=<LCSC-num> --output ../lib/lib`

## Building the netlist and importing it to KiCAD

`ato build` is the tool for you!

For example: `ato build --target=netlist-kicad6`

This will generate a netlist in the `build` directory.

Then, from within the KiCAD layout, which is stored in `elec/layout/default`, you can import the netlist with:

1. File -> Import Netlist
![Import Netlist](images/file-import.png)
1. Select the netlist you've just generated. The output is in the terminal, but it should approximately be servo-drive/build/servo-drive.net
2. Make sure you're using unique IDs, rather than designators (though they should work too)
3. Ruthlessly destroy stuff that's not supposed to be there (check boxes on the right)
![Import Netlist 2](images/import-settings.png)
1. Check the errors - sometimes it's important
