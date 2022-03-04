<div align="center">

# faebryk

<a href="https://github.com/faebryk/faebryk">
<img height=300 width=300 src="./faebryk_logo.png"/>
</a>
<br/>

Open-source software-defined EDA

[![Version](https://img.shields.io/github/v/tag/faebryk/faebryk)](https://github.com/faebryk/faebryk/releases) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/faebryk/faebryk/blob/main/LICENSE) [![Pull requests open](https://img.shields.io/github/issues-pr/faebryk/faebryk)](https://github.com/faebryk/faebryk/pulls) [![Issues open](https://img.shields.io/github/issues/faebryk/faebryk)](https://github.com/faebryk/faebryk/issues)
[![Discord](https://img.shields.io/discord/907675333350809600?label=Discord)](https://discord.com/channels/907675333350809600) [![PyPI - Downloads](https://img.shields.io/pypi/dm/faebryk?label=PyPi%20Downloads)](https://pypi.org/project/faebryk/) [![GitHub commit activity](https://img.shields.io/github/commit-activity/m/faebryk/faebryk)](https://github.com/faebryk/faebryk/commits/main)

</div>

## Get running
Setup
```
> git clone git@github.com:faebryk/faebryk.git
> cd faebryk
> git submodule init
> git submodule update
> pip install -r requirements.txt
```
Run
```
> ./samples/experiment.py | tail -n1 > netlist.net
```

## Running your own experiments/Making samples
First follow the steps in get running.
Then add a file in samples/ (you can use experiment.py as template).
Call your file with `python3 samples/<yourfile>.py`.

## Running tests
Setup
```
> pip install -r test/requirements.txt
```
Run
```
> python3 test/test.py
```


## Dependencies
- networkx

## Contibuting
See [CONTRIBUTING.md](CONTRIBUTING.md)

## Community Support
Community support is provided via Discord; see the Resources below for details.

### Resources
- Source Code: https://github.com/faebryk/faebryk
- Chat: Real-time chat happens in faebryk's Discord Server. Use this Discord [Invite](https://discord.gg/95jYuPmnUW) to register
- Issues: https://github.com/faebryk/faebryk/issues
