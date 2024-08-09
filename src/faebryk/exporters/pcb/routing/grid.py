"""
TODO: Explain file
"""

import logging
import math
import re
from abc import ABC, abstractmethod
from typing import Generic, Self, TypeVar

import graph_tool.all as gt
import networkx as nx
import numpy as np

# logging settings
logger = logging.getLogger(__name__)

RESOLUTION = 0.1  # mm
DIAGONALS = True
WEIGHTS = (10, 15, 10000)

T = TypeVar("T", int, float)


class GridException(Exception): ...


class GridInvalidVertexException(GridException):
    def __init__(self, vertex_index: int, graph: "Graph") -> None:
        self.vertex_index = vertex_index
        self.graph = graph
        super().__init__(f"Invalid vertex: {vertex_index}")

    def get_coord(self, grid: "Grid"):
        return grid._project_out(self.vertex_index)


class Coord(Generic[T], np.ndarray):
    EPS = 0.05

    def __new__(cls, x: T, y: T, z: T):
        obj = np.asarray([x, y, z]).view(cls)
        return obj

    @classmethod
    def from_coord(cls, coord: "Coord"):
        return cls(*coord)

    @property
    def x(self):
        return self[0]

    @property
    def y(self):
        return self[1]

    @property
    def z(self):
        return self[2]

    def is_float(self):
        return isinstance(self.x, float)

    def as_tuple(self):
        return tuple(self)

    def __str__(self):
        rounding = 2 if self.is_float() else 0
        return f"2D({tuple(round(c, rounding) for c in self)})"

    def __repr__(self) -> str:
        return str(self)

    def quantize(self, resolution: float):
        return round(self / resolution) * resolution

    def __round__(self, x=0):
        return Coord(*(round(i, x) for i in self))

    def __add__(self, other):
        return Coord(*super().__add__(other))

    def __mul__(self, other):
        return Coord(*super().__mul__(other))

    def __sub__(self, other):
        return Coord(*super().__sub__(other))

    def __lt__(self, other):
        return super().__lt__(other)

    def __truediv__(self, other):
        return Coord(*super().__truediv__(other))

    def __hash__(self) -> int:
        return hash(tuple(self))

    def __eq__(self, x):
        if isinstance(x, tuple):
            x = Coord(*x)
        if x is None:
            return self is None
        assert isinstance(x, Coord)
        return all(abs(x - self) < self.EPS)

    def __ne__(self, x):
        return not x == self

    def __bool__(self) -> bool:
        return True

    def __ceil__(self):
        return Coord(*(math.ceil(x) for x in self))


IntCoord = int
intCoord = tuple[int, int, int]
OutCoord = Coord[float]


def sub(c1: intCoord, c2: intCoord):
    return tuple(x - y for x, y in zip(c1, c2))


def add(c1: intCoord, c2: intCoord):
    return tuple(map(sum, zip(c1, c2)))


def eq(c1: intCoord, c2: intCoord):
    return all([_c1 == _c2 for _c1, _c2 in zip(c1, c2)])


T = TypeVar("T")


class Graph(Generic[T], ABC):
    def __init__(self, G: T, steps):
        self.G = G
        self.steps = steps

    def project_out(self, coord: IntCoord) -> intCoord:
        out = (
            coord % self.steps[0],
            (coord // self.steps[0]) % self.steps[1],
            coord // (self.steps[0] * self.steps[1]),
        )
        return out

    def project_into(self, coord: intCoord) -> IntCoord:
        out = int(
            coord[0]
            + coord[1] * self.steps[0]
            + coord[2] * self.steps[1] * self.steps[0]
        )
        return out

    @staticmethod
    @abstractmethod
    def _lattice(dims: tuple[int, int], weight: int): ...

    @abstractmethod
    def add_edges(self, edges: np.ndarray, weight: float): ...

    @abstractmethod
    def vertices(self) -> set[IntCoord]: ...

    @abstractmethod
    def subgraph(
        self,
        ex: set[IntCoord] | np.ndarray | None = None,
        inc: set[IntCoord] | np.ndarray | None = None,
    ) -> Self: ...

    @abstractmethod
    def neigh(self, vs: set[IntCoord], order: int, ring: bool) -> set[IntCoord]: ...

    @abstractmethod
    def astar(self, start: IntCoord, end: IntCoord, h=None) -> list[IntCoord]: ...

    @abstractmethod
    def stack(self): ...

    def diagonal_edges_lattice(self):
        dims = self.steps[:2]
        # Create an array for all possible i, j combinations
        i, j = np.meshgrid(range(dims[0] - 1), range(dims[1] - 1), indexing="ij")

        # Create edge tuples for both diagonal directions
        edges1 = np.stack((i, j, i + 1, j + 1), axis=-1).reshape(-1, 2, 2)
        edges2 = np.stack((i + 1, j, i, j + 1), axis=-1).reshape(-1, 2, 2)

        # Concatenate them together
        edges = np.concatenate((edges1, edges2), axis=0)

        e_i = (edges[..., 1] * dims[0] + edges[..., 0]).reshape(-1, 2)

        return e_i

    def layer_edges_lattice(self):
        dims = self.steps

        layer_node_count = dims[0] * dims[1]
        left = np.arange(layer_node_count)
        stacks = tuple(
            np.stack(
                [
                    left + layer_node_count * z1,
                    left + layer_node_count * z2,
                ],
                axis=-1,
            )
            for z1 in range(dims[2])
            for z2 in range(dims[2])
            if z1 > z2
        )
        out = np.concatenate(
            stacks,
            axis=0,
        )

        return out

    @classmethod
    def lattice(cls, dims: tuple[int, int, int], diagonal: bool, layer: bool):
        g = cls(cls._lattice(dims[:2], weight=WEIGHTS[0]), dims)

        if diagonal:
            # Add diagonals
            logger.info("Building diagonals")
            diagonals = g.diagonal_edges_lattice()
            logging.info(f"Adding diagonals {len(diagonals)}")
            g.add_edges(diagonals, weight=WEIGHTS[1])

        if layer and dims[2] > 1:
            logger.info("Building layers")
            g.stack()
            layer_edges = g.layer_edges_lattice()
            g.add_edges(layer_edges, weight=WEIGHTS[2])

        return g

    def distance(self, a: IntCoord, b: IntCoord = 0) -> float:
        # if not ex.isdisjoint({a, b}):
        #     return 9999999

        tuples = tuple(self.project_out(x) for x in (b, a))
        # manhattan
        # out = sum(map(abs, sub(*tuples)))
        # euclid
        out = math.sqrt(sum(x**2 for x in sub(*tuples)))
        # logger.info(f"Distance({tuples}) = {out}")
        return out

    def find_path(self, nodes: set[IntCoord], ex: set[IntCoord]) -> list[IntCoord]:
        logger.info(f"Find path for {[self.project_out(n) for n in nodes]}")

        def sub_path(start: IntCoord, end: IntCoord) -> list[IntCoord]:
            logger.info(
                f"Find path between {[self.project_out(n) for n in (start, end)]}"
            )
            out = self.astar(
                start,
                end,
                h=self.distance,
            )
            if not out:
                raise nx.NetworkXNoPath("No path found")

            if not ex.isdisjoint(out):
                raise nx.NetworkXNoPath("Crossed illegal domain")

            # logger.info(f"Found: {out}")
            return out

        if len(nodes) == 2:
            return sub_path(*nodes)

        nodes_left = list(nodes)
        cur = min(nodes_left, key=self.distance)
        nodes_left.remove(cur)
        path = [cur]

        while nodes_left:
            heur_pick = min(nodes_left, key=lambda x: self.distance(cur, x))
            nodes_left.remove(heur_pick)
            path.extend(sub_path(cur, heur_pick)[1:])
            cur = heur_pick

        return path


class GraphTool(Graph[gt.Graph]):
    def make_exception(self, e: ValueError) -> Exception:
        msg: str = e.args[0]
        m = re.match(r"^Invalid vertex index: ([0-9]*)$", msg)
        if m is not None:
            return GridInvalidVertexException(int(m.group(1)), self)

        return e

    @staticmethod
    def _lattice(dims: tuple[int, int], weight: int):
        G = gt.lattice(list(dims))
        weights = G.new_edge_property("int32_t")
        G.ep["weight"] = weights
        weights.a = weight

        return G

    def stack(self):
        g = self.G
        weights = g.ep["weight"]
        g.add_edge_list(
            np.concatenate(
                [
                    g.get_edges([weights]) + ([self.project_into((0, 0, z))] * 2 + [0])
                    for z in range(1, self.steps[2])
                ]
            ),
            eprops=[weights],
        )

    def add_edges(self, edges: np.ndarray, weight: int):
        logger.info("Add edges & weight to graph")
        weights = self.G.ep["weight"]
        edges = np.hstack([edges, np.full((edges.shape[0], 1), weight)])
        self.G.add_edge_list(edges, eprops=[weights])

    def vertices(self):
        return set(self.G.vertex_index[v] for v in self.G.vertices())

    def subgraph(
        self,
        ex: set[IntCoord] | np.ndarray | None = None,
        inc: set[IntCoord] | np.ndarray | None = None,
    ):
        ex_used = ex is not None and len(ex) > 0
        inc_used = inc is not None and len(inc) > 0
        if not ex_used and not inc_used:
            return self

        keep = self.G.new_vertex_property("bool", vals=not inc_used)

        def conv(set_or_array: set[IntCoord] | np.ndarray) -> np.ndarray:
            if isinstance(set_or_array, np.ndarray):
                return set_or_array
            return np.array(list(set_or_array))

        if inc_used:
            keep.a[conv(inc)] = True

        if ex_used:
            keep.a[conv(ex)] = False

        return GraphTool(
            gt.GraphView(self.G, vfilt=keep),
            self.steps,
        )

    def subgraph_e(self, ex: set[tuple[IntCoord, IntCoord]] | np.ndarray):
        logging.info(f"Subgraph ex={len(ex)}")
        if not ex:
            return self

        # TODO maybe the only way to make this fast is to understand the link
        #  (v1_index,v2_index) -> edge_index

        keep = self.G.new_edge_property("bool", vals=True)
        edge_objs = [e_obj for e in ex if (e_obj := self.G.edge(*e))]

        try:
            for e in edge_objs:
                keep[e] = False
        except ValueError as e:
            raise self.make_exception(e)

        return GraphTool(
            gt.GraphView(self.G, efilt=keep),
            self.steps,
        )

    def neigh(self, vs: set[IntCoord], order: int, ring: bool):
        """
        if ring is true only look in for neighbours with same z coordinate
        """

        # TODO can be implemented numerically

        idx_p = self.G.vertex_index

        if order == 0:
            return vs
        return self.neigh(
            {
                v_n
                for v in vs
                for v_n, i in self.G.get_all_neighbors(v, vprops=[idx_p])
                if not ring or self.project_out(i)[2] == self.project_out(v)[2]
            },
            order=order - 1,
            ring=ring,
        )

    def astar(self, start: IntCoord, end: IntCoord, h=None) -> list[IntCoord]:
        G = self.G

        source = G.vertex(start)
        target = G.vertex(end)

        path, _ = gt.shortest_path(
            G,
            source,
            target,
            G.ep["weight"],
        )

        return [G.vertex_index[p] for p in path]


# from igraph import Graph as iGraph
# class IGraph(Graph[iGraph]):
#    @staticmethod
#    def _lattice(dims: tuple[int, int], weight: int):
#        return iGraph.Lattice(dim=list(dims), circular=False)
#
#    def add_edges(self, edges: np.ndarray, weight: int):
#        self.G.add_edges(edges)
#
#    def vertices(self):
#        return set(self.G.vs.indices)
#
#    def subgraph(self, ex: set[IntCoord]):
#        G = self.G.copy()
#        G.delete_edges(G.es.select(_source=ex))
#
#        return IGraph(G, self.steps)
#
#    def neigh(self, vs, order: int):
#        return {x for n_neigh in self.G.neighborhood(vs, order=order) for x in n_neigh}
#
#    def astar(self, start: IntCoord, end: IntCoord, h=None) -> list[IntCoord]:
#        return self.G.get_shortest_path_astar(
#            start,
#            end,
#            heuristics=(lambda _, __, ___: 1)
#            if h is None
#            else (lambda _, a, b: h(a, b)),
#        )


GRAPH = GraphTool


class Grid:
    def __init__(
        self,
        rect: tuple[OutCoord, OutCoord],
        inclusion_poly: list[list[OutCoord]] | None = None,
        resolution_=RESOLUTION,
        tolerance_=5,  # mm
    ) -> None:
        self.resolution = OutCoord(resolution_, resolution_, 1)
        tolerance = Coord(tolerance_, tolerance_, 0)
        self.rect = (rect[0] - tolerance, rect[1] + tolerance)

        steps = math.ceil((self.rect[1] - self.rect[0]) / self.resolution) + 1
        self.steps = steps
        self.used: set[IntCoord] = set()

        logger.info(f"Building {steps} grid for Rect {rect}")

        self.G = GRAPH.lattice(
            tuple(self.steps),
            diagonal=DIAGONALS,
            layer=True,
        )

        logger.info(f"Adding {len(inclusion_poly or [])} inclusion zones to grid")
        if inclusion_poly and len(inclusion_poly) == 1:
            inc = self._project_poly_into(inclusion_poly[0])
        else:
            inc = {
                coord
                for poly in inclusion_poly or []
                for coord in self._project_poly_into(poly)
            }
        self.G = self.G.subgraph(inc=inc)

    def _project_out(self, coord: IntCoord) -> OutCoord:
        out_t = self.G.project_out(coord)
        out = self._project_outof_tuple(out_t)
        # logger.info(f"{out} <- {out_t} <- {coord}")
        return out

    def _project_into(self, coord: OutCoord) -> IntCoord:
        out_i = self._project_into_tuple(coord)
        out = self.G.project_into(out_i)
        # logger.info(f"{coord} -> {out_i} -> {out}")
        return out

    def _project_outof_tuple(self, coord: intCoord) -> OutCoord:
        out = OutCoord(*coord) * self.resolution + self.rect[0]
        return out

    def _project_into_tuple(self, coord: OutCoord) -> intCoord:
        out = tuple(map(int, round((coord - self.rect[0]) / self.resolution)))
        return out

    def _project_rect_into(self, rect: tuple[OutCoord, OutCoord]) -> list[IntCoord]:
        out = []
        TOLERANCE = 1
        # tolerance = OutCoord(TOLERANCE, TOLERANCE, 0)

        qrect = tuple(self._project_into_tuple(r) for r in rect)

        qrect_dim = sub(qrect[1], qrect[0])

        out = [
            self.G.project_into(add(qrect[0], (x, y, z)))
            for x in range(-TOLERANCE, qrect_dim[0] + 1 + TOLERANCE)
            for y in range(-TOLERANCE, qrect_dim[1] + 1 + TOLERANCE)
            for z in range(qrect_dim[2] + 1)
        ]

        assert out
        return out

    def _project_poly_into_shape(self, poly: list[OutCoord]) -> list[IntCoord]:
        from shapely import box, intersection
        from shapely.geometry import Point, Polygon

        cpoly = [self._project_into_tuple(coord)[:2] for coord in poly]
        spoly = Polygon(cpoly)

        # assert ints
        assert all(abs(int(x) - x) < 0.001 for x in spoly.bounds)
        assert len(set(c[2] for c in poly)) == 1, "Cross-dimensional polygon"

        bounds = box(0, 0, self.steps[0], self.steps[1])
        bounded_spoly = intersection(spoly, bounds)

        minx, miny, maxx, maxy = map(int, bounded_spoly.bounds)

        zs = [next(iter(bounded_spoly.exterior.coords))[2]]
        if zs[0] < 0:
            zs = list(range(self.steps[2]))

        poly_points = [
            self.G.project_into((int(x), int(y), int(z)))
            for x in range(minx, maxx)
            for y in range(miny, maxy)
            if Point(x, y).within(bounded_spoly)
            for z in zs
        ]

        return poly_points

    def _project_poly_into(self, poly: list[OutCoord]) -> list[IntCoord] | np.ndarray:
        from matplotlib.path import Path

        cpoly = [self._project_into_tuple(coord)[:2] for coord in poly]
        dims = self.steps[0], self.steps[1]

        # assert ints
        assert len(set(c[2] for c in poly)) == 1, "Cross-dimensional polygon"

        zs = [next(iter(poly))[2]]
        if zs[0] < 0:
            zs = list(range(self.steps[2]))

        x, y = np.meshgrid(np.arange(dims[0]), np.arange(dims[1]))
        x, y = x.flatten(), y.flatten()
        points = np.vstack((x, y)).T

        p = Path(cpoly)  # make a polygon
        grid = p.contains_points(points)
        int_points = np.where(grid)[0]

        d = dims[0] * dims[1]
        multidim = np.concatenate([int_points + z * d for z in zs], axis=-1)

        return multidim

    def reproject(self, coord: OutCoord) -> OutCoord:
        return self._project_out(self._project_into(coord))

    def find_path(
        self,
        nodes: list[OutCoord],
        exclusion_points: set[OutCoord] | None = None,
        exclusion_rects: set[tuple[OutCoord, OutCoord]] | None = None,
        # inclusion_poly: list[list[OutCoord]] | None = None,
        layer_exclusion_rects: set[tuple[OutCoord, OutCoord]] | None = None,
        remove: bool = True,
        compressed: bool = True,
    ) -> list[OutCoord]:
        logger.info("-" * 80)
        logger.info(f"Find outcoord path for {nodes}")

        # Translate OutCoord to internal
        exclusion_coords = {self._project_into(x) for x in exclusion_points or {}}
        exclusion_coords |= {
            coord
            for rect in exclusion_rects or {}
            for coord in self._project_rect_into(rect)
        }
        node_coords = {self._project_into(x) for x in nodes}
        used = self.G.neigh(self.used, order=1, ring=True)
        ex = exclusion_coords | used

        logger.info("Run checks")

        # Checks
        if not node_coords.isdisjoint(exclusion_coords):
            hits = node_coords.intersection(exclusion_coords)
            logger.warning(
                f"In exclusion: {hits} {set(self._project_out(hit) for hit in hits)}"
            )
            raise Exception()

        if not node_coords.isdisjoint(used):
            logger.warning("In use")
            raise Exception()

        # TODO reimplement, but fast
        # v_set = self.G.vertices()
        # if not node_coords.issubset(v_set):
        #    logger.warning(f"Not in graph: {node_coords.difference(v_set)}")
        #    raise Exception()

        # TODO combine with node sub
        # Remove cross-layer edges if on any layer in use
        logger.info("Remove inter-layer edges in zones")

        G = self.G

        def all_layers(coords: set[IntCoord]):
            coords_np = np.array(list(coords))
            return np.stack(
                [
                    (coords_np + self.G.project_into((0, 0, z)))
                    % (self.steps[0] * self.steps[1] * self.steps[2])
                    for z in range(self.steps[2])
                ],
                axis=-1,
            )

        def inter_layer_edges(coords):
            return {(abc[0], e) for abc in all_layers(coords) for e in abc[1:]}

        layer_exclusion_coords = {
            coord
            for rect in layer_exclusion_rects or {}
            for coord in self._project_rect_into(rect)
        } | exclusion_coords

        if not remove:
            layer_exclusion_coords |= used

        # TODO make efficient
        G = G.subgraph_e(ex=inter_layer_edges(layer_exclusion_coords))

        logger.info("Build node subgraph")
        G = G.subgraph(ex=ex, inc=None)

        path = G.find_path(
            nodes=node_coords,
            ex=ex,
        )

        if remove:
            self.used |= set(path)
            self.G = self.G.subgraph_e(ex=inter_layer_edges(path))

        projected_out_path = [self._project_out(c) for c in path]

        if compressed:
            projected_out_path = self._compress_path(projected_out_path)

        return projected_out_path

    @staticmethod
    def _compress_path(path: list[OutCoord]):
        if not path:  # if path is empty
            return []

        compressed_path = []
        vector = None

        for last, cur in zip(path[:-1], path[1:]):
            now_vector = cur - last
            if now_vector != vector:
                compressed_path.append(last)
                vector = now_vector

        compressed_path.append(path[-1])  # Add the last point

        return compressed_path

    def draw(self):
        g = self.G.G
        # weights = g.ep["weight"]
        dims = self.steps

        vlayer = g.new_vertex_property("int16_t")
        for z in range(dims[2]):
            x = dims[0] * dims[1]
            vlayer.a[x * z : x * (z + 1)] = z

        vused = g.new_vertex_property("string")
        for v in g.vertices():
            vused[v] = "green"
        for v in self.used:
            vused[v] = "red"

        logger.info("Draw")
        gt.graph_draw(
            g,
            pos=gt.sfdp_layout(g, cooling_step=0.95, epsilon=1e-2),
            vertex_text=g.vertex_index,
            output="graph_app.png",
            bg_color="white",
            vertex_color=vused,
            vertex_fill_color=vlayer,
            # edge_pen_width=weights,
            output_size=(4096, 2160),
        )
