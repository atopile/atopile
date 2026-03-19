# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""Backward-compatible import path for EasyEDA builders."""

from faebryk.libs.easyeda._footprint import FootprintBuilder
from faebryk.libs.easyeda._symbol import SymbolBuilder

__all__ = ["FootprintBuilder", "SymbolBuilder"]
