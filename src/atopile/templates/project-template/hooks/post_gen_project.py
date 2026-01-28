#!/usr/bin/env python
import pathlib

if __name__ == "__main__":
    # Create layouts directory
    layouts_dir = pathlib.Path("layouts")
    layouts_dir.mkdir(exist_ok=True)

    # Remove LICENSE file if not open source
    if "Not open source" == "{{ cookiecutter.license }}":
        try:
            pathlib.Path("LICENSE.txt").unlink()
        except FileNotFoundError:
            pass
