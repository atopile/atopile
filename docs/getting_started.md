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

`ato view --root-file led.ato --root-node led.ato/LED`

You should get a browser window popping up and wham! bam! alakazam! you've got a component!

## Adding footprints to your project

[JLCPCB](https://jlcpcb.com/) is a great place to get cheap PCBs made. They have a [library](https://jlcpcb.com/parts) of footprints that you can use.

To pull in a footprint, we've been using the wonderful tool [easyeda2kicad](https://pypi.org/project/easyeda2kicad/).

Add it to your python environment with `pip install easyeda2kicad`

Then you can download JLCPCB/EasyEDA/LCSC footprints with `easyeda2kicad --full --lcsc_id=<LCSC-num> --output ../lib/lib`
