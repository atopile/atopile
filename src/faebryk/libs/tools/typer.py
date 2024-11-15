# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import typer


def typer_callback(parent: typer.Typer | None, **callback_args):
    def wrap(func):
        new_app = typer.Typer(rich_markup_mode="rich")
        if parent is not None:
            parent.add_typer(new_app)

        new_app.callback(name=func.__name__, **callback_args)(func)

        return new_app

    return wrap
