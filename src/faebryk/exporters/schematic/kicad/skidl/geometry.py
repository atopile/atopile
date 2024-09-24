# -*- coding: utf-8 -*-

# The MIT License (MIT) - Copyright (c) Dave Vandenbout.

from math import sqrt, sin, cos, radians
from copy import copy

from ..utilities import export_to_all

__all__ = [
    "mms_per_mil",
    "mils_per_mm",
    "Vector",
    "tx_rot_0",
    "tx_rot_90",
    "tx_rot_180",
    "tx_rot_270",
    "tx_flip_x",
    "tx_flip_y",
]


"""
Stuff for handling geometry:
    transformation matrices,
    points,
    bounding boxes,
    line segments.
"""

# Millimeters/thousandths-of-inch conversion factor.
mils_per_mm = 39.37008
mms_per_mil = 0.0254


@export_to_all
def to_mils(mm):
    """Convert millimeters to thousandths-of-inch and return."""
    return mm * mils_per_mm


@export_to_all
def to_mms(mils):
    """Convert thousandths-of-inch to millimeters and return."""
    return mils * mms_per_mil


@export_to_all
class Tx:
    def __init__(self, a=1, b=0, c=0, d=1, dx=0, dy=0):
        """Create a transformation matrix.
        tx = [
               a  b  0
               c  d  0
               dx dy 1
             ]
        x' = a*x + c*y + dx
        y' = b*x + d*y + dy
        """
        self.a = a
        self.b = b
        self.c = c
        self.d = d
        self.dx = dx
        self.dy = dy

    @classmethod
    def from_symtx(cls, symtx):
        """Return a Tx() object that implements the "HVLR" geometric operation sequence.

        Args:
            symtx (str): A string of H, V, L, R operations that are applied in sequence left-to-right.

        Returns:
            Tx: A transformation matrix that implements the sequence of geometric operations.
        """
        op_dict = {
            "H": Tx(a=-1, c=0, b=0, d=1),  # Horizontal flip.
            "V": Tx(a=1, c=0, b=0, d=-1),  # Vertical flip.
            "L": Tx(a=0, c=-1, b=1, d=0),  # Rotate 90 degrees left (counter-clockwise).
            "R": Tx(a=0, c=1, b=-1, d=0),  # Rotate 90 degrees right (clockwise).
        }

        tx = Tx()
        for op in symtx.upper():
            tx *= op_dict[op]
        return tx

    def __repr__(self):
        return "{self.__class__}({self.a}, {self.b}, {self.c}, {self.d}, {self.dx}, {self.dy})".format(
            self=self
        )

    def __str__(self):
        return "[{self.a}, {self.b}, {self.c}, {self.d}, {self.dx}, {self.dy}]".format(
            self=self
        )

    def __mul__(self, m):
        """Return the product of two transformation matrices."""
        if isinstance(m, Tx):
            tx = m
        else:
            # Assume m is a scalar, so convert it to a scaling Tx matrix.
            tx = Tx(a=m, d=m)
        return Tx(
            a=self.a * tx.a + self.b * tx.c,
            b=self.a * tx.b + self.b * tx.d,
            c=self.c * tx.a + self.d * tx.c,
            d=self.c * tx.b + self.d * tx.d,
            dx=self.dx * tx.a + self.dy * tx.c + tx.dx,
            dy=self.dx * tx.b + self.dy * tx.d + tx.dy,
        )

    @property
    def origin(self):
        """Return the (dx, dy) translation as a Point."""
        return Point(self.dx, self.dy)

    # This setter doesn't work in Python 2.7.18.
    # @origin.setter
    # def origin(self, pt):
    #     """Set the (dx, dy) translation from an (x,y) Point."""
    #     self.dx, self.dy = pt.x, pt.y

    @property
    def scale(self):
        """Return the scaling factor."""
        return (Point(1, 0) * self - Point(0, 0) * self).magnitude

    def move(self, vec):
        """Return Tx with movement vector applied."""
        return self * Tx(dx=vec.x, dy=vec.y)

    def rot_90cw(self):
        """Return Tx with 90-deg clock-wise rotation around (0, 0)."""
        return self * Tx(a=0, b=1, c=-1, d=0)

    def rot(self, degs):
        """Return Tx rotated by the given angle (in degrees)."""
        rads = radians(degs)
        return self * Tx(a=cos(rads), b=sin(rads), c=-sin(rads), d=cos(rads))

    def flip_x(self):
        """Return Tx with X coords flipped around (0, 0)."""
        return self * Tx(a=-1)

    def flip_y(self):
        """Return Tx with Y coords flipped around (0, 0)."""
        return self * Tx(d=-1)

    def no_translate(self):
        """Return Tx with translation set to (0,0)."""
        return Tx(a=self.a, b=self.b, c=self.c, d=self.d)


# Some common rotations.
tx_rot_0 = Tx(a=1, b=0, c=0, d=1)
tx_rot_90 = Tx(a=0, b=1, c=-1, d=0)
tx_rot_180 = Tx(a=-1, b=0, c=0, d=-1)
tx_rot_270 = Tx(a=0, b=-1, c=1, d=0)

# Some common flips.
tx_flip_x = Tx(a=-1, b=0, c=0, d=1)
tx_flip_y = Tx(a=1, b=0, c=0, d=-1)


@export_to_all
class Point:
    def __init__(self, x, y):
        """Create a Point with coords x,y."""
        self.x = x
        self.y = y

    def __hash__(self):
        """Return hash of X,Y tuple."""
        return hash((self.x, self.y))

    def __eq__(self, other):
        """Return true if (x,y) tuples of self and other are the same."""
        return (self.x, self.y) == (other.x, other.y)

    def __lt__(self, other):
        """Return true if (x,y) tuple of self compares as less than (x,y) tuple of other."""
        return (self.x, self.y) < (other.x, other.y)

    def __ne__(self, other):
        """Return true if (x,y) tuples of self and other differ."""
        return not (self == other)

    def __add__(self, pt):
        """Add the x,y coords of pt to self and return the resulting Point."""
        if not isinstance(pt, Point):
            pt = Point(pt, pt)
        return Point(self.x + pt.x, self.y + pt.y)

    def __sub__(self, pt):
        """Subtract the x,y coords of pt from self and return the resulting Point."""
        if not isinstance(pt, Point):
            pt = Point(pt, pt)
        return Point(self.x - pt.x, self.y - pt.y)

    def __mul__(self, m):
        """Apply transformation matrix or scale factor to a point and return a point."""
        if isinstance(m, Tx):
            return Point(
                self.x * m.a + self.y * m.c + m.dx, self.x * m.b + self.y * m.d + m.dy
            )
        elif isinstance(m, Point):
            return Point(self.x * m.x, self.y * m.y)
        else:
            return Point(m * self.x, m * self.y)

    def __rmul__(self, m):
        if isinstance(m, Tx):
            raise ValueError
        else:
            return self * m

    def xprod(self, pt):
        """Cross-product of two 2D vectors returns scalar in Z coord."""
        return self.x * pt.y - self.y * pt.x

    def mask(self, msk):
        """Multiply the X & Y coords by the elements of msk."""
        return Point(self.x * msk[0], self.y * msk[1])

    def __neg__(self):
        """Negate both coords."""
        return Point(-self.x, -self.y)

    def __truediv__(self, d):
        """Divide the x,y coords by d."""
        return Point(self.x / d, self.y / d)

    def __div__(self, d):
        """Divide the x,y coords by d."""
        return Point(self.x / d, self.y / d)

    def round(self):
        return Point(int(round(self.x)), int(round(self.y)))

    def __str__(self):
        return "{} {}".format(self.x, self.y)

    def snap(self, grid_spacing):
        """Snap point x,y coords to the given grid spacing."""
        snap_func = lambda x: int(grid_spacing * round(x / grid_spacing))
        return Point(snap_func(self.x), snap_func(self.y))

    def min(self, pt):
        """Return a Point with coords that are the min x,y of both points."""
        return Point(min(self.x, pt.x), min(self.y, pt.y))

    def max(self, pt):
        """Return a Point with coords that are the max x,y of both points."""
        return Point(max(self.x, pt.x), max(self.y, pt.y))

    @property
    def magnitude(self):
        """Get the distance of the point from the origin."""
        return sqrt(self.x**2 + self.y**2)

    @property
    def norm(self):
        """Return a unit vector pointing from the origin to the point."""
        try:
            return self / self.magnitude
        except ZeroDivisionError:
            return Point(0, 0)

    def flip_xy(self):
        """Flip X-Y coordinates of point."""
        self.x, self.y = self.y, self.x

    def __repr__(self):
        return "{self.__class__}({self.x}, {self.y})".format(self=self)

    def __str__(self):
        return "({}, {})".format(self.x, self.y)


Vector = Point


@export_to_all
class BBox:
    def __init__(self, *pts):
        """Create a bounding box surrounding the given points."""
        inf = float("inf")
        self.min = Point(inf, inf)
        self.max = Point(-inf, -inf)
        self.add(*pts)

    def __add__(self, obj):
        """Return the merged BBox of two BBoxes or a BBox and a Point."""
        sum_ = BBox()
        if isinstance(obj, Point):
            sum_.min = self.min.min(obj)
            sum_.max = self.max.max(obj)
        elif isinstance(obj, BBox):
            sum_.min = self.min.min(obj.min)
            sum_.max = self.max.max(obj.max)
        else:
            raise NotImplementedError
        return sum_

    def __iadd__(self, obj):
        """Update BBox bt adding another Point or BBox"""
        sum_ = self + obj
        self.min = sum_.min
        self.max = sum_.max
        return self

    def add(self, *objs):
        """Update the bounding box size by adding Point/BBox objects."""
        for obj in objs:
            self += obj
        return self

    def __mul__(self, m):
        return BBox(self.min * m, self.max * m)

    def round(self):
        return BBox(self.min.round(), self.max.round())

    def is_inside(self, pt):
        """Return True if point is inside bounding box."""
        return (self.min.x <= pt.x <= self.max.x) and (self.min.y <= pt.y <= self.max.y)

    def intersects(self, bbox):
        """Return True if the two bounding boxes intersect."""
        return (
            (self.min.x < bbox.max.x)
            and (self.max.x > bbox.min.x)
            and (self.min.y < bbox.max.y)
            and (self.max.y > bbox.min.y)
        )

    def intersection(self, bbox):
        """Return the bounding box of the intersection between the two bounding boxes."""
        if not self.intersects(bbox):
            return None
        corner1 = self.min.max(bbox.min)
        corner2 = self.max.min(bbox.max)
        return BBox(corner1, corner2)

    def resize(self, vector):
        """Expand/contract the bounding box by applying vector to its corner points."""
        return BBox(self.min - vector, self.max + vector)

    def snap_resize(self, grid_spacing):
        """Resize bbox so max and min points are on grid.

        Args:
            grid_spacing (float): Grid spacing.
        """
        bbox = self.resize(Point(grid_spacing - 1, grid_spacing - 1))
        bbox.min = bbox.min.snap(grid_spacing)
        bbox.max = bbox.max.snap(grid_spacing)
        return bbox

    @property
    def area(self):
        """Return area of bounding box."""
        return self.w * self.h

    @property
    def w(self):
        """Return the bounding box width."""
        return abs(self.max.x - self.min.x)

    @property
    def h(self):
        """Return the bounding box height."""
        return abs(self.max.y - self.min.y)

    @property
    def ctr(self):
        """Return center point of bounding box."""
        return (self.max + self.min) / 2

    @property
    def ll(self):
        """Return lower-left point of bounding box."""
        return Point(self.min.x, self.min.y)

    @property
    def lr(self):
        """Return lower-right point of bounding box."""
        return Point(self.max.x, self.min.y)

    @property
    def ul(self):
        """Return upper-left point of bounding box."""
        return Point(self.min.x, self.max.y)

    @property
    def ur(self):
        """Return upper-right point of bounding box."""
        return Point(self.max.x, self.max.y)

    def __repr__(self):
        return "{self.__class__}(Point({self.min}), Point({self.max}))".format(
            self=self
        )

    def __str__(self):
        return "[{}, {}]".format(self.min, self.max)


@export_to_all
class Segment:
    def __init__(self, p1, p2):
        "Create a line segment between two points."
        self.p1 = copy(p1)
        self.p2 = copy(p2)

    def __mul__(self, m):
        """Apply transformation matrix to a segment and return a segment."""
        return Segment(self.p1 * m, self.p2 * m)

    def round(self):
        return Segment(self.p1.round(), self.p2.round())

    def __str__(self):
        return "{} {}".format(str(self.p1), str(self.p2))

    def flip_xy(self):
        """Flip the X-Y coordinates of the segment."""
        self.p1.flip_xy()
        self.p2.flip_xy()

    def intersects(self, other):
        """Return true if the segments intersect."""

        # FIXME: This fails if the segments are parallel!
        raise NotImplementedError

        # Given two segments:
        #   self: p1 + (p2-p1) * t1
        #   other: p3 + (p4-p3) * t2
        # Look for a solution t1, t2 that solves:
        #   p1x + (p2x-p1x)*t1 = p3x + (p4x-p3x)*t2
        #   p1y + (p2y-p1y)*t1 = p3y + (p4y-p3y)*t2
        # If t1 and t2 are both in range [0,1], then the two segments intersect.

        p1x, p1y, p2x, p2y = self.p1.x, self.p1.y, self.p2.x, self.p2.y
        p3x, p3y, p4x, p4y = other.p1.x, other.p1.y, other.p2.x, other.p2.y

        # denom = p1x*p3y - p1x*p4y - p1y*p3x + p1y*p4x - p2x*p3y + p2x*p4y + p2y*p3x - p2y*p4x
        # denom = p1x * (p3y - p4y) + p1y * (p4x - p3x) + p2x * (p4y - p3y) + p2y * (p3x - p4x)
        denom = (p1x - p2x) * (p3y - p4y) + (p1y - p2y) * (p4x - p3x)

        try:
            # t1 = (p1x*p3y - p1x*p4y - p1y*p3x + p1y*p4x + p3x*p4y - p3y*p4x) / denom
            # t2 = (-p1x*p2y + p1x*p3y + p1y*p2x - p1y*p3x - p2x*p3y + p2y*p3x) / denom
            t1 = ((p1y - p3y) * (p4x - p3x) - (p1x - p3x) * (p4y - p3y)) / denom
            t2 = ((p1y - p3y) * (p2x - p3x) - (p1x - p3x) * (p2y - p3y)) / denom
        except ZeroDivisionError:
            return False

        return (0 <= t1 <= 1) and (0 <= t2 <= 1)

    def shadows(self, other):
        """Return true if two segments overlap each other even if they aren't on the same horiz or vertical track."""

        if self.p1.x == self.p2.x and other.p1.x == other.p2.x:
            # Horizontal segments. See if their vertical extents overlap.
            self_min = min(self.p1.y, self.p2.y)
            self_max = max(self.p1.y, self.p2.y)
            other_min = min(other.p1.y, other.p2.y)
            other_max = max(other.p1.y, other.p2.y)
        elif self.p1.y == self.p2.y and other.p1.y == other.p2.y:
            # Verttical segments. See if their horizontal extents overlap.
            self_min = min(self.p1.x, self.p2.x)
            self_max = max(self.p1.x, self.p2.x)
            other_min = min(other.p1.x, other.p2.x)
            other_max = max(other.p1.x, other.p2.x)
        else:
            # Segments aren't horizontal or vertical, so neither can shadow the other.
            return False

        # Overlap conditions based on segment endpoints.
        return other_min < self_max and other_max > self_min
