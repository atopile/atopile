#!/usr/bin/env python
import pathlib

if __name__ == "__main__":
    if "Not open source" == "{{ cookiecutter.license }}":
        try:
            pathlib.Path("LICENSE").unlink()
        except FileNotFoundError:
            pass
