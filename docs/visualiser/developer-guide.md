# Visualiser Developer Guide

## Getting started

Don't forget to install all the development deps: `pip install -e ."[dev]"`

## Running the visualiser

From the root of the project, run: `uvicorn atopile.visualiser.server:app --reload`

The `--reload` option will automatically reload the server when there's been a change to the `server.py` file (or maybe even everything in the project? I'm not sure)
