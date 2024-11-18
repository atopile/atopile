# -*- coding: utf-8 -*-

# The MIT License (MIT) - Copyright (c) Dave Vandenbout.

"""
KiCad 5 drawing objects.
"""

from dataclasses import dataclass


@dataclass
class DrawDef:
    name: str
    ref: str
    zero: str
    name_offset: int
    show_nums: bool
    show_names: bool
    num_units: int
    lock_units: bool
    power_symbol: bool


@dataclass
class DrawF0:
    ref: str
    x: float
    y: float
    size: float
    orientation: str
    visibility: str
    halign: str
    valign: str


@dataclass
class DrawF1:
    name: str
    x: float
    y: float
    size: float
    orientation: str
    visibility: str
    halign: str
    valign: str
    fieldname: str


@dataclass
class DrawArc:
    cx: float
    cy: float
    radius: float
    start_angle: float
    end_angle: float
    unit: int
    dmg: int
    thickness: float
    fill: str
    startx: float
    starty: float
    endx: float
    endy: float


@dataclass
class DrawCircle:
    cx: float
    cy: float
    radius: float
    unit: int
    dmg: int
    thickness: float
    fill: str


@dataclass
class DrawPoly:
    point_count: int
    unit: int
    dmg: int
    thickness: float
    points: list
    fill: str


@dataclass
class DrawRect:
    x1: float
    y1: float
    x2: float
    y2: float
    unit: int
    dmg: int
    thickness: float
    fill: str


@dataclass
class DrawText:
    angle: float
    x: float
    y: float
    size: float
    hidden: bool
    unit: int
    dmg: int
    text: str
    italic: bool
    bold: bool
    halign: str
    valign: str


@dataclass
class DrawPin:
    name: str
    num: str
    x: float
    y: float
    length: float
    orientation: str
    num_size: float
    name_size: float
    unit: int
    dmg: int
    electrical_type: str
    shape: str
