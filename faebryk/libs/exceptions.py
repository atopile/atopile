# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


class FaebrykException(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)
