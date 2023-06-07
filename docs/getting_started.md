# Getting Started

## Syntax highlighting is pretty nice...

Copy `src/vscode_extension` to `~/.vscode/extensions/`
eg. `cp -r src/vscode_extension ~/.vscode/extensions/atopile`

## Creating a new project

The easiest way to create a new project at the moment is to clone from an example, eg. `git clone https://gitlab.atopile.io/atopile/bike-light.git`

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
