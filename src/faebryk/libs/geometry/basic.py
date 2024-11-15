# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import math
from operator import add
from typing import Iterable, Sequence, TypeVar

import numpy as np
from shapely import MultiPolygon, Point, Polygon, transform

logger = logging.getLogger(__name__)


def polygon_insert_cutout(polygon: Polygon, cutout: Polygon) -> Polygon:
    """
    Insert a cutout into a polygon

    :param polygon: The polygon to insert the cutout into
    :param cutout: The cutout to insert
    :return: The polygon with the cutout inserted
    """

    p_coords = list(polygon.exterior.coords)
    c_coords = list(cutout.exterior.coords)

    dist = [
        (Geometry.distance_euclid(p1, p2), p1, p2) for p1, p2 in zip(p_coords, c_coords)
    ]

    _, p_closest, c_closest = min(dist, key=lambda x: x[0])

    # roll the cutout so that the closest point is first, then append the first point to
    # close the cutout
    c_first_idx = c_coords.index(c_closest)
    c_coords = list(np.roll(c_coords, -c_first_idx, axis=0))
    c_coords.append(c_coords[0])

    # Insert the cutout into the polygon
    p_first_idx = p_coords.index(p_closest)
    flattened_coords = (
        p_coords[:p_first_idx]
        + [p_coords[p_first_idx]]
        + c_coords
        + p_coords[p_first_idx:]
    )

    return Polygon(flattened_coords)


def flatten_polygons(polygons: list[Polygon]) -> list[Polygon]:
    """
    Flatten a list of polygons by removing polygons that are contained in other polygons

    :param polygons: The polygons to flatten
    :return: The flattened polygons
    """
    flattened_polygons = []
    while polygons:
        remaining = []
        for poly in polygons:
            # skip lower level polygons
            if any([p.contains(poly) for p in polygons if p != poly]):
                remaining.append(poly)
                continue
            # cut out polygons that are contained in other polygons
            if any([z.contains(poly) for z in flattened_polygons]):
                flattened_polygons = [
                    polygon_insert_cutout(z, poly) if z.contains(poly) else z
                    for z in flattened_polygons
                ]
            else:
                # add polygons that are not contained in any other polygon
                flattened_polygons.append(poly)
        polygons = remaining

    return flattened_polygons


def get_distributed_points_in_polygon(
    polygon: Polygon,
    density: float,
) -> list[Point]:
    """
    Get a list of points that are distributed in a polygon

    :param polygon: The polygon to distribute the points in
    :param density: The density of the points
    :return: A list of points that are distributed in the polygon
    """

    num_points = int(polygon.area * density)
    if polygon.area > 0 and num_points == 0:
        num_points = 1

    points = get_random_points_in_polygon(polygon, num_points)

    min_x, min_y, max_x, max_y = polygon.bounds
    size_x = max_x - min_x
    size_y = max_y - min_y

    while True:
        point_distance_travel = []
        for i, point in enumerate(points):
            point_bubble = polygon

            for p in points:
                if p == point:
                    continue

                p1 = np.array((point.x, point.y))
                p2 = np.array((p.x, p.y))

                p_mid = (p1 + p2) / 2

                v = p2 - p1
                v_unit = v / np.linalg.norm(v)
                v_unit_perp = np.array([v_unit[1], -v_unit[0]])

                # create a polygon at least twice as large to cut the polygon up
                exclusion_polygon = Polygon(
                    [
                        (
                            p_mid[0] + v_unit_perp[0] * size_x / 2,
                            p_mid[1] + v_unit_perp[1] * size_x / 2,
                        ),
                        (
                            p_mid[0] + v_unit_perp[0] * size_x / 2 + v_unit[0] * size_y,
                            p_mid[1] + v_unit_perp[1] * size_x / 2 + v_unit[1] * size_y,
                        ),
                        (
                            p_mid[0] - v_unit_perp[0] * size_x / 2 + v_unit[0] * size_y,
                            p_mid[1] - v_unit_perp[1] * size_x / 2 + v_unit[1] * size_y,
                        ),
                        (
                            p_mid[0] - v_unit_perp[0] * size_x,
                            p_mid[1] - v_unit_perp[1] * size_x,
                        ),
                    ]
                )

                point_bubble = point_bubble.difference(exclusion_polygon)

            assert point_bubble.contains(point)

            if isinstance(point_bubble, MultiPolygon):
                for p in list(point_bubble.geoms):
                    if p.contains(point):
                        point_bubble = p
                        break

            new_point = point_bubble.centroid

            # TODO: it is possible it will be outside, then just move it to the
            # closest point on the polygon.
            if not point_bubble.contains(new_point):
                continue

            assert polygon.contains(new_point)

            point_distance_travel.append(
                Geometry.distance_euclid(
                    Geometry.Point((point.x, point.y)),
                    Geometry.Point((new_point.x, new_point.y)),
                )
            )
            logger.debug(
                f"Point ({point.x:.2f}, {point.y:.2f}) -> ({new_point.x:.2f}, "
                f"{new_point.y:.2f}), distance: {point_distance_travel[-1]}"
            )

            points[i] = new_point

        if max(point_distance_travel) < density / 100:
            break

    return points


def closest_point_on_segment_to_point(line: tuple[Point, Point], point: Point) -> Point:
    """
    Finds the minimum distance from the point to the line defined by two points

    :param line: The line segment defined by two points
    :param point: The point to find the distance to
    :return: The closest point on the line segment to the point
    """
    if line[0] == line[1]:
        return line[0]

    p1 = np.array((line[0].x, line[0].y))
    p2 = np.array((line[1].x, line[1].y))
    p3 = np.array((point.x, point.y))

    v_line = p2 - p1
    v_point = p3 - p1

    # Project point_vec onto line_vec
    v_line_unit = v_line / np.linalg.norm(v_line)

    # Unit vector in direction of line_vec
    proj_length = np.dot(v_point, v_line_unit)  # Projection length

    if proj_length < 0:
        # The projection falls before p1
        closest_point = p1
    elif proj_length > np.linalg.norm(v_line):
        # The projection falls after p2
        closest_point = p2
    else:
        # The projection falls within the segment
        proj_vec = proj_length * v_line_unit  # Projection vector
        closest_point = p1 + proj_vec

    p = Point(*closest_point)

    assert p != Point(), f"Could not find closes point on line {line} to point {point}"

    return p


def closest_point_on_line(p1, p2, p3):
    """
    Finds the closest point on the line defined by p1 and p2 to the point p3.

    Parameters:
    p1, p2, p3: Arrays or lists representing the coordinates of the points.

    Returns:
    The coordinates of the closest point on the line to p3.
    """
    # Convert points to numpy arrays
    p1 = np.array(p1)
    p2 = np.array(p2)
    p3 = np.array(p3)

    # Vector from p1 to p2
    line_vec = p2 - p1
    # Vector from p1 to p3
    point_vec = p3 - p1

    # Project point_vec onto line_vec
    line_vec_unit = line_vec / np.linalg.norm(
        line_vec
    )  # Unit vector in direction of line_vec
    proj_length = np.dot(point_vec, line_vec_unit)  # Projection length
    proj_vec = proj_length * line_vec_unit  # Projection vector

    # Closest point on the line
    closest_point = p1 + proj_vec

    return closest_point


def get_random_points_in_polygon(polygon: Polygon, num_points: int) -> list[Point]:
    """
    Get a list of unique random points that are inside a polygon

    :param polygon: The polygon to get the points from
    :param num_points: The number of points to get
    :return: A list of unique random points that are inside the polygon
    """
    points = []
    min_x, min_y, max_x, max_y = polygon.bounds
    while len(points) < num_points:
        p = Point(np.random.uniform(min_x, max_x), np.random.uniform(min_y, max_y))
        if polygon.contains(p) and p not in points:
            points.append(p)
    return points


def polygon_to_lines(polygon: Polygon) -> Iterable[tuple[Point, Point]]:
    coords = [Point(p) for p in polygon.exterior.coords]
    coords += [coords[0]]
    for i in range(len(polygon.exterior.coords) - 1):
        yield (coords[i], coords[i + 1])


def intersect_polygon_with_grid(
    polys: list[Polygon],
    grid_pitch: tuple[float, float],
    grid_offset: tuple[float, float],
) -> list[Point]:
    """
    Get a list of points on a grid that are inside a list of non-intersecting polygons

    :param polys: The polygons to check, can be either an exterior or interior polygon
    :param grid_pitch: The pitch of the grid (x, y)
    :param grid_offset: The offset of the grid (x, y)
    :return: A list of points that are inside the polygons
    """

    points = []
    min_x, min_y, max_x, max_y = (math.inf, math.inf, -math.inf, -math.inf)
    for b in [(p.bounds) for p in polys]:
        min_x = min(min_x, b[0])
        min_y = min(min_y, b[1])
        max_x = max(max_x, b[2])
        max_y = max(max_y, b[3])

    grid_start_x = math.ceil(min_x / grid_pitch[0]) * grid_pitch[0] + grid_offset[0]
    grid_start_y = math.ceil(min_y / grid_pitch[1]) * grid_pitch[1] + grid_offset[1]
    grid_x = np.arange(grid_start_x, max_x, grid_pitch[0])
    grid_y = np.arange(grid_start_y, max_y, grid_pitch[1])

    fill_polys = []
    keepout_polys = []

    # only support one level of keepout, no fills inside keepouts
    for poly in polys:
        if any([p.contains(poly) for p in polys if p != poly]):
            keepout_polys.append(poly)
            continue
        fill_polys.append(poly)

    for poly in fill_polys:
        points += [
            Point(x, y)
            for x in grid_x
            for y in grid_y
            if poly.contains(Point(x, y))
            and not any([p.contains(Point(x, y)) for p in keepout_polys])
        ]

    return points


def transform_polygon(
    poly: Polygon, offset: tuple[float, float], scale: tuple[float, float]
) -> Polygon:
    """
    Transform a list of polygons using a transformation matrix

    :param polys: The polygons to transform
    :param offset: The offset to apply (x, y)
    :param scale: The scale to apply (x, y)

    :return: The transformed polygons
    """

    return transform(poly, lambda x: (x + offset) * scale)


# TODO: cleanup and merge
class Geometry:
    Point2D = tuple[float, float]
    Point = tuple[float, float, float, int]

    @staticmethod
    def add_points(p1: Point | Point2D, p2: Point | Point2D) -> Point | Point2D:
        p1e = p1 + (0,) * (4 - len(p1))
        p2e = p2 + (0,) * (4 - len(p2))
        out = tuple(map(add, p1e, p2e))
        if len(p1) == len(p2) == 2:
            return out[:2]
        return out

    # class Point2D(tuple[float, float]):
    #    def __add__(self, other: "Geometry.Point2D") -> "Geometry.Point2D":
    #        return Geometry.Point2D(self[0] + other[0], self[1] + other[1])

    ## TODO fix all Point2D functions to use Point

    ## TODO more generic
    ## x,y, rotation, layer
    ## Point = tuple[float, float, float, int]

    # class Point(tuple[float, float, float, int]):
    #    def __round__(self, ndigits=None) -> Point:
    #        return Point(
    #            round(self[0], ndigits=ndigits),
    #            round(self[1], ndigits=ndigits),
    #            round(self[2], ndigits=ndigits),
    #            self[3],
    #        )

    #    def twod(self) -> "Geometry.Point2D":
    #        return Geometry.Point2D(self[:2])

    #    @property
    #    def x(self) -> float:
    #        return self[0]

    #    @property
    #    def y(self) -> float:
    #        return self[1]

    #    @property
    #    def rotation_deg(self) -> float:
    #        return self[2]

    #    @property
    #    def layer(self) -> int:
    #        return self[3]

    #    def __add__(self, other: "Point | Geometry.Point2D") -> Point:
    #        if isinstance(other, Geometry.Point2D):
    #            other = Point(other[0], other[1], 0, self.layer)

    #        assert self.layer == other.layer

    #        return Point(
    #            self.x + other.x,
    #            self.y + other.y,
    #            # TODO does this make sense?
    #            self.rotation_deg + other.rotation_deg,
    #            self.layer,
    #        )

    @staticmethod
    def mirror(axis: tuple[float | None, float | None], structure: list[Point2D]):
        return [
            (
                2 * axis[0] - x if axis[0] is not None else x,
                2 * axis[1] - y if axis[1] is not None else y,
            )
            for (x, y) in structure
        ]

    @staticmethod
    def as2d(coord: Point | Point2D) -> Point2D:
        return coord[:2]

    @staticmethod
    def as4d(coord: Point | Point2D) -> Point:
        return coord + (0,) * (4 - len(coord))

    @staticmethod
    def abs_pos(parent_: Point | Point2D, child_: Point | Point2D) -> Point:
        # Extend to x,y,rotation,layer
        parent = Geometry.as4d(parent_)
        child = Geometry.as4d(child_)

        rot_parent = parent[2]
        rot_child = child[2]
        total_rot_deg = rot_parent + rot_child

        # Rotate child vector around parent and add
        # rotation deg is negative because kicad rotates counter clock wise
        parent_absolute_xy = parent[:2]
        child_relative_xy = child[:2]
        x, y = parent_absolute_xy
        cx_rotated, cy_rotated = Geometry.rotate(
            (0, 0), [child_relative_xy], -rot_parent
        )[0]
        abs_x = x + cx_rotated
        abs_y = y + cy_rotated

        # Layer
        parent_layer = parent[3]
        child_layer = child[3]
        if parent_layer != 0 and child_layer != 0:
            raise Exception(
                f"Adding two non-zero layers: {parent_layer=} + {child_layer=}"
            )
        layer = parent_layer + child_layer

        out = (
            abs_x,
            abs_y,
            total_rot_deg,
            layer,
        )

        return out

    @staticmethod
    def translate(vec: Point2D, structure: list[Point2D]) -> list[Point2D]:
        return [tuple(map(add, vec, point)) for point in structure]

    @classmethod
    def rotate(
        cls, axis: Point2D, structure: list[Point2D], angle_deg: float
    ) -> list[Point2D]:
        theta = np.radians(angle_deg)
        c, s = np.cos(theta), np.sin(theta)
        R = np.array(((c, -s), (s, c)))

        return cls.translate(
            axis,
            [
                tuple(R @ np.array(point))
                for point in cls.translate((-axis[0], -axis[1]), structure)
            ],
        )

    C = TypeVar("C", tuple[float, float], tuple[float, float, float])

    @staticmethod
    def triangle(start: C, width: float, depth: float, count: int):
        x1, y1 = start[:2]

        n = count - 1
        cy = width / n

        ys = [round(y1 + cy * i, 2) for i in range(count)]
        xs = [round(x1 + depth * (1 - abs(1 - 1 / n * i * 2)), 2) for i in range(count)]

        return list(zip(xs, ys))

    @staticmethod
    def line(start: C, length: float, count: int):
        x1, y1 = start[:2]

        n = count - 1
        cy = length / n

        ys = [round(y1 + cy * i, 2) for i in range(count)]
        xs = [x1] * count

        return list(zip(xs, ys))

    @staticmethod
    def line2(start: C, end: C, count: int):
        x1, y1 = start[:2]
        x2, y2 = end[:2]

        n = count - 1
        cx = (x2 - x1) / n
        cy = (y2 - y1) / n

        ys = [round(y1 + cy * i, 2) for i in range(count)]
        xs = [round(x1 + cx * i, 2) for i in range(count)]

        return list(zip(xs, ys))

    @staticmethod
    def find_circle_center(p1, p2, p3):
        """
        Finds the center of the circle passing through the three given points.
        """
        # Compute the midpoints
        mid1 = (p1 + p2) / 2
        mid2 = (p2 + p3) / 2

        # Compute the slopes of the lines
        m1 = (p2[1] - p1[1]) / (p2[0] - p1[0])
        m2 = (p3[1] - p2[1]) / (p3[0] - p2[0])

        # The slopes of the perpendicular bisectors
        perp_m1 = -1 / m1
        perp_m2 = -1 / m2

        # Equations of the perpendicular bisectors
        # y = perp_m1 * (x - mid1[0]) + mid1[1]
        # y = perp_m2 * (x - mid2[0]) + mid2[1]

        # Solving for x
        x = (mid2[1] - mid1[1] + perp_m1 * mid1[0] - perp_m2 * mid2[0]) / (
            perp_m1 - perp_m2
        )

        # Solving for y using one of the bisector equations
        y = perp_m1 * (x - mid1[0]) + mid1[1]

        return np.array([x, y])

    @staticmethod
    def approximate_arc(
        p_start: Point2D, p_mid: Point2D, p_end: Point2D, resolution=10
    ) -> list[tuple[Point2D, Point2D]]:
        p_start, p_mid, p_end = (np.array(p) for p in (p_start, p_mid, p_end))

        # Calculate the center of the circle
        center = Geometry.find_circle_center(p_start, p_mid, p_end)

        # Calculate start, mid, and end angles
        start_angle = np.arctan2(p_start[1] - center[1], p_start[0] - center[0])
        mid_angle = np.arctan2(p_mid[1] - center[1], p_mid[0] - center[0])
        end_angle = np.arctan2(p_end[1] - center[1], p_end[0] - center[0])

        # Adjust angles if necessary
        if start_angle > mid_angle:
            start_angle -= 2 * np.pi
        if mid_angle > end_angle:
            mid_angle -= 2 * np.pi

        # Radius of the circle
        r = np.linalg.norm(p_start - center)

        # Compute angles of line segment endpoints
        angles = np.linspace(start_angle, end_angle, resolution + 1)

        # Compute points on the arc
        points = np.array(
            [[center[0] + r * np.cos(a), center[1] + r * np.sin(a)] for a in angles]
        )

        # Create line segments
        segments = [(points[i], points[i + 1]) for i in range(resolution)]

        seg_no_np = [(tuple(a), tuple(b)) for a, b in segments]

        return seg_no_np

    @staticmethod
    def distance_euclid(p1: Point, p2: Point):
        return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)

    @staticmethod
    def bbox(
        points: Sequence[Point | Point2D], tolerance=0.0
    ) -> tuple[Point2D, Point2D]:
        min_x = min(p[0] for p in points)
        min_y = min(p[1] for p in points)
        max_x = max(p[0] for p in points)
        max_y = max(p[1] for p in points)

        return (
            min_x - tolerance,
            min_y - tolerance,
        ), (
            max_x + tolerance,
            max_y + tolerance,
        )

    @staticmethod
    def rect_to_polygon(rect: tuple[Point2D, Point2D]) -> list[Point2D]:
        return [
            (rect[0][0], rect[0][1]),
            (rect[1][0], rect[0][1]),
            (rect[1][0], rect[1][1]),
            (rect[0][0], rect[1][1]),
        ]

    @staticmethod
    def average(points: list[Point2D | Point]) -> Point:
        points4d = [p + (0,) * (4 - len(p)) for p in points]
        # same layer
        assert len({p[3] for p in points4d}) == 1
        points2d = [p[:2] for p in points4d]

        out = tuple(np.mean(points2d, axis=0))
        if any(len(p) > 2 for p in points):
            return out + (0, points[0][3])
