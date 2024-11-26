# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


class UserException(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)
