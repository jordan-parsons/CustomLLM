"""Construction layer: generators that emit candidate unit-distance graphs.

All coordinates are exact. All edge sets are derived by exact detection inside
UDGraph, never asserted by these functions.
"""

from __future__ import annotations

from fractions import Fraction as F
from typing import List, Sequence

from .field import DEGREY_FIELD, MultiQuadField, Rat
from .graph import UDGraph
from .point import Point, Rotation, dedup_points, minkowski_sum, spindle_rotation


def _P(field: MultiQuadField, xc, yc) -> Point:
    return Point(field.elem(xc), field.elem(yc))


def origin(field: MultiQuadField = DEGREY_FIELD) -> Point:
    return Point(field.zero(), field.zero())


def rat_point(field: MultiQuadField, x, y) -> Point:
    return Point(field.rational(x), field.rational(y))


# --------------------------------------------------------------------------
# Base figures
# --------------------------------------------------------------------------
def unit_hexagon_points(field: MultiQuadField = DEGREY_FIELD) -> List[Point]:
    """Centre plus the 6 vertices of a regular hexagon of side 1 (H, 7 points)."""
    o = origin(field)
    p0 = rat_point(field, 1, 0)
    pts = [o]
    for k in range(6):
        pts.append(Rotation.by_degrees_60k(field, k).apply(p0))
    return dedup_points(pts)


def unit_hexagon(field: MultiQuadField = DEGREY_FIELD) -> UDGraph:
    return UDGraph(unit_hexagon_points(field), lineage={"op": "unit_hexagon"})


def triangle_points(field: MultiQuadField = DEGREY_FIELD) -> List[Point]:
    """Unit equilateral triangle with a vertex at the origin."""
    return [
        origin(field),
        rat_point(field, 1, 0),
        Point(field.rational(F(1, 2)), field.sqrt_gen(3) * F(1, 2)),
    ]


def rhombus_points(field: MultiQuadField = DEGREY_FIELD) -> List[Point]:
    """Unit rhombus O,u,u+v,v (two equilateral triangles). Long diagonal sqrt(3)."""
    o = origin(field)
    u = rat_point(field, 1, 0)
    v = Point(field.rational(F(1, 2)), field.sqrt_gen(3) * F(1, 2))
    return [o, u, u + v, v]


def moser_spindle() -> UDGraph:
    """The Moser spindle: 7 vertices, 11 edges, chromatic number 4.

    Two unit rhombi sharing the origin, the second rotated by the angle a with
    cos a = 5/6 so that the two far apexes (each at distance sqrt(3) from the
    origin) land at exactly unit distance.
    """
    field = DEGREY_FIELD
    rh = rhombus_points(field)
    rot = spindle_rotation(field)
    o = origin(field)
    rh2 = [rot.apply(p, center=o) for p in rh]
    pts = dedup_points(rh + rh2)
    g = UDGraph(pts, lineage={"op": "moser_spindle"})
    return g


def golomb_graph() -> UDGraph:
    """The Golomb graph: 10 vertices, 18 edges, chromatic number 4.

    Unit wheel (centre + hexagon of side 1) plus a unit equilateral triangle of
    circumradius 1/sqrt(3), rotated by the angle d with cos d = sqrt(3)/6,
    sin d = sqrt(33)/6, which places each triangle vertex at exactly unit
    distance from one alternating hexagon vertex.

    Derivation of that angle (exact): for a triangle vertex at radius
    1/sqrt(3) and a hexagon vertex at radius 1, squared distance is
    1/3 + 1 - (2/sqrt(3))cos d, which equals 1 iff cos d = sqrt(3)/6.
    """
    field = DEGREY_FIELD
    pts = unit_hexagon_points(field)
    # T0 = (1/6, sqrt(11)/6): radius^2 = 1/36 + 11/36 = 1/3, and
    # |T0 - (1,0)|^2 = 25/36 + 11/36 = 1 exactly.
    t0 = Point(field.rational(F(1, 6)), field.sqrt_gen(11) * F(1, 6))
    tri = [Rotation.by_degrees_60k(field, 2 * k).apply(t0) for k in range(3)]
    return UDGraph(dedup_points(pts + tri), lineage={"op": "golomb_graph"})


# --------------------------------------------------------------------------
# Generic search moves
# --------------------------------------------------------------------------
def minkowski(A: Sequence[Point], B: Sequence[Point], lineage=None) -> UDGraph:
    return UDGraph(minkowski_sum(A, B), lineage=lineage or {"op": "minkowski"})


def spindle(points: Sequence[Point], rot: Rotation, center: Point) -> List[Point]:
    """Union of a point set with its rotated copy about `center`."""
    return dedup_points(list(points) + [rot.apply(p, center=center) for p in points])


def rotate_all(points: Sequence[Point], rot: Rotation, center: Point) -> List[Point]:
    return [rot.apply(p, center=center) for p in points]


def translate_all(points: Sequence[Point], delta: Point) -> List[Point]:
    return [p + delta for p in points]


def overlay(*point_sets: Sequence[Point]) -> List[Point]:
    out: List[Point] = []
    for s in point_sets:
        out.extend(s)
    return dedup_points(out)


# --------------------------------------------------------------------------
# Adversarial fixtures for the detector test suite
# --------------------------------------------------------------------------
def near_unit_rational_pair(field: MultiQuadField = DEGREY_FIELD):
    """Two points whose squared distance is rational and ~1 + 1.7e-10, not 1.

    x = 5/6 + 1e-10, y = sqrt(11)/6. Then d^2 = x^2 + 11/36 which is exactly
    1 + (5/3)e-10 + 1e-20: a float comparison at 1e-9 tolerance accepts it.
    """
    eps = Rat(1, 10 ** 10)
    x = field.rational(F(5, 6) + eps)
    y = field.sqrt_gen(11) * F(1, 6)
    return origin(field), Point(x, y)


def near_unit_irrational_pair(field: MultiQuadField = DEGREY_FIELD):
    """Squared distance ~1 but with a nonzero sqrt(33) component.

    x = 5/6, y = (sqrt(11) + sqrt(3)/1e10)/6. Then
    d^2 = 25/36 + (11 + 2*sqrt(33)/1e10 + 3/1e20)/36, whose sqrt(33)
    coefficient is exactly 2/(36e10) != 0, so d^2 != 1 exactly, while the
    floating-point value rounds to 1.0000000000...
    """
    x = field.rational(F(5, 6))
    delta = field.sqrt_gen(3) * Rat(1, 10 ** 10)
    y = (field.sqrt_gen(11) + delta) * F(1, 6)
    return origin(field), Point(x, y)


def exact_unit_pair_hard(field: MultiQuadField = DEGREY_FIELD):
    """A genuinely unit pair whose coordinates are irrational in both slots."""
    p = Point(field.sqrt_gen(3) * F(1, 3), field.sqrt_gen(11) * F(1, 11))
    # Build q = p + (unit vector at the spindle angle) so d(p,q) == 1 exactly.
    rot = spindle_rotation(field)
    u = rot.apply(rat_point(field, 1, 0))
    return p, p + u
