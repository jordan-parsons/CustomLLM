"""Ambient point-pool I/O and generation helpers (CONSTRUCTOR C1).

A *pool* is an exact, deduplicated set of Points in one MultiQuadField. It is not
a graph: no edge set is implied. Pools are the ambient search space handed to the
minimizer; the minimizer selects subsets and UDGraph re-derives the edges by
exact detection.

On-disk format (JSON, exactly reloadable):

    {"field": [3, 5, 11],
     "n": 2306,
     "points": [{"x": [[num, den], ...2^k pairs...],
                 "y": [[num, den], ...]}, ...],
     "meta": {...free-form provenance...}}

This is deliberately the same "field"/"points" shape UDGraph.to_dict() emits, so
UDGraph.from_dict() can consume a pool file directly (it re-detects edges) and
load_pool() can consume a UDGraph file directly.

NOTHING here uses floating point to decide anything. Coordinates are exact field
elements; deduplication is by exact canonical key; every unit distance is decided
by hn.detect (float prefilter + mandatory exact confirmation).
"""

from __future__ import annotations

import json
import os
from fractions import Fraction as F
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .detect import detect_edges
from .field import MultiQuadField
from .point import Point, dedup_points

POOL_DIR = "/home/user/CustomLLM/data/pools"


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------
def save_pool(
    path: str, points: Sequence[Point], meta: Optional[Dict] = None
) -> str:
    """Write an exact pool to JSON. Exactly reloadable by load_pool()."""
    if not points:
        raise ValueError("empty pool")
    field = points[0].field
    for p in points:
        if p.field != field:
            raise TypeError("mixed fields in pool")
    keys = {p.key() for p in points}
    if len(keys) != len(points):
        raise ValueError(
            f"pool is not exactly deduplicated ({len(points)} points, "
            f"{len(keys)} distinct) - call dedup_points first"
        )
    d = {
        "field": list(field.gens),
        "n": len(points),
        "points": [
            {
                "x": [[c.numerator, c.denominator] for c in p.x.coeffs],
                "y": [[c.numerator, c.denominator] for c in p.y.coeffs],
            }
            for p in points
        ],
        "meta": meta or {},
    }
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as fh:
        json.dump(d, fh, separators=(",", ":"))
    return path


def load_pool(path: str) -> Tuple[List[Point], MultiQuadField]:
    """Read an exact pool (or a UDGraph dict) back. No floats involved."""
    with open(path) as fh:
        d = json.load(fh)
    field = MultiQuadField(tuple(d["field"]))
    pts = [
        Point(
            field.elem([F(a, b) for a, b in pd["x"]]),
            field.elem([F(a, b) for a, b in pd["y"]]),
        )
        for pd in d["points"]
    ]
    return pts, field


# ---------------------------------------------------------------------------
# Field embedding
# ---------------------------------------------------------------------------
def embed_points(points: Sequence[Point], target: MultiQuadField) -> List[Point]:
    """Embed points of a subfield into `target` exactly (no coordinate invented)."""
    out = []
    for p in points:
        src = p.field
        if src == target:
            out.append(p)
        else:
            out.append(Point(target.embed(src, p.x), target.embed(src, p.y)))
    return out


# ---------------------------------------------------------------------------
# Exact statistics
# ---------------------------------------------------------------------------
def pool_stats(points: Sequence[Point]) -> Dict:
    """Exact edge count and degree statistics for a pool."""
    edges = detect_edges(points)
    n = len(points)
    deg = [0] * n
    for u, v in edges:
        deg[u] += 1
        deg[v] += 1
    return {
        "n": n,
        "m": len(edges),
        "max_degree": max(deg) if n else 0,
        "mean_degree": (2 * len(edges) / n) if n else 0.0,
        "edges": edges,
        "degrees": deg,
    }


def induced_edge_count(points: Sequence[Point], subset_keys) -> int:
    """Exact number of unit edges induced on the sub-pool with these keys."""
    sub = [p for p in points if p.key() in subset_keys]
    return len(detect_edges(sub))


def contains_keys(points: Sequence[Point], keys) -> Tuple[int, int]:
    """(#keys present, #keys total) - exact subset test by canonical key."""
    have = {p.key() for p in points}
    keys = set(keys)
    return (len(keys & have), len(keys))


# ---------------------------------------------------------------------------
# Exact square roots inside a multiquadratic field
# ---------------------------------------------------------------------------
def _squarefree_divisors(field: MultiQuadField) -> List[int]:
    """The 2^k products of distinct generators - the only radicands the field has."""
    out = [1]
    for g in field.gens:
        out += [d * g for d in out]
    return sorted(out)


def _sqrt_rational(field: MultiQuadField, q: F):
    """sqrt(q) as a field element, or None if not expressible. Exact.

    sqrt(num/den) = sqrt(num*den)/den, and sqrt(n) lies in the field iff
    n = s^2 * d for some d dividing prod(gens) squarefree-ly. There are only 2^k
    such d, so we test those directly instead of factoring n (which can be a
    several-hundred-digit integer and is not tractable by trial division).
    """
    if q < 0:
        return None
    if q == 0:
        return field.zero()
    from math import isqrt

    num, den = q.numerator, q.denominator
    n = num * den
    for d in _squarefree_divisors(field):
        if n % d:
            continue
        m = n // d
        s = isqrt(m)
        if s * s != m:
            continue
        if d == 1:
            return field.rational(F(s, den))
        return field.sqrt_gen(d) * F(s, den)
    return None


def field_sqrt(e):
    """Exact square root of `e` inside its own MultiQuadField, or None.

    Algorithm: descent on the highest radical present. Writing e = A + B*sqrt(r)
    with A, B in the subfield K omitting sqrt(r), any square root in
    F = K(sqrt(r)) has the form x + y*sqrt(r) with x, y in K, and then

        x^2 + r*y^2 = A,   2*x*y = B   =>   x^2 = (A +- sqrt(A^2 - r*B^2)) / 2

    so sqrt(A^2 - r*B^2) must itself lie in K. Recurse. Every returned value is
    re-verified by exact multiplication (result*result == e) before it is
    handed back, so a bug here can only ever produce None, never a wrong root.
    """
    field = e.field
    if e.is_zero():
        return field.zero()
    if e.sign() < 0:
        return None
    if e.is_rational():
        r = _sqrt_rational(field, e.coeffs[0])
    else:
        r = _sqrt_split(e)
    if r is None:
        return None
    if not (r * r == e):  # exact self-certification
        return None
    return r


def _sqrt_split(e):
    field = e.field
    top = max(s for s, v in enumerate(e.coeffs) if v != 0)
    i = top.bit_length() - 1
    bit = 1 << i
    r = field.gens[i]
    a = [F(0)] * field.dim
    b = [F(0)] * field.dim
    for s, v in enumerate(e.coeffs):
        if v == 0:
            continue
        if s & bit:
            b[s ^ bit] += v
        else:
            a[s] += v
    from .field import FieldElem

    A = FieldElem(field, tuple(a))
    B = FieldElem(field, tuple(b))
    if B.is_zero():
        return None
    D = A * A - (B * B) * r
    sD = field_sqrt(D)
    if sD is None:
        return None
    half = F(1, 2)
    for cand in (A + sD, A - sD):
        x2 = cand * half
        if x2.is_zero():
            continue
        x = field_sqrt(x2)
        if x is None:
            continue
        try:
            y = (B * half) / x
        except ZeroDivisionError:
            continue
        root = x + field.sqrt_gen(r) * y
        if root * root == e:
            return root
    return None


# ---------------------------------------------------------------------------
# Exact pairs at a prescribed squared distance
# ---------------------------------------------------------------------------
def detect_pairs_at_sqdist(points: Sequence[Point], target, window: float = 1e-6):
    """Index pairs at EXACTLY squared distance `target` (a rational).

    Same contract as hn.detect.detect_edges: the float grid is a *prefilter*
    only; every surviving pair is confirmed by exact arithmetic
    (`sqdist(...).equals_rational(target)`). Used only to choose rotation
    centres and to enumerate circle-intersection candidates -- unit EDGES are
    always and only produced by hn.detect.detect_edges.
    """
    import math
    from collections import defaultdict

    tq = F(target)
    d = math.sqrt(float(tq))
    cell = max(d, 1.0)
    approx = [p.approx() for p in points]
    buckets = defaultdict(list)
    for i, (x, y) in enumerate(approx):
        buckets[(math.floor(x / cell), math.floor(y / cell))].append(i)
    reach = int(math.ceil(d / cell)) + 1
    out = []
    rng = range(-reach, reach + 1)
    tf = float(tq)
    for (cx, cy), idxs in buckets.items():
        neigh = []
        for dx in rng:
            for dy in rng:
                neigh.extend(buckets.get((cx + dx, cy + dy), ()))
        for i in idxs:
            xi, yi = approx[i]
            pi = points[i]
            for j in neigh:
                if j <= i:
                    continue
                xj, yj = approx[j]
                if abs((xi - xj) ** 2 + (yi - yj) ** 2 - tf) > window:
                    continue  # FILTER ONLY
                if pi.sqdist(points[j]).equals_rational(tq):  # EXACT DECISION
                    out.append((i, j))
    out.sort()
    return out


def circle_intersections(a: Point, b: Point):
    """The <=2 points at EXACT distance 1 from both a and b, if they exist in the field.

    With q = |a-b|^2, w = perp(b-a) (so |w|^2 = q) and m = (a+b)/2, the solutions
    are m +- t*w where t^2 = (4-q)/(4q). Exact throughout: the routine returns []
    unless (4-q)/(4q) is genuinely a square in the field, and every returned
    point is re-verified with the exact unit-distance predicate.
    """
    field = a.field
    dv = b - a
    q = dv.x * dv.x + dv.y * dv.y
    if q.is_zero():
        return []
    s = (field.rational(4) - q) / (q * 4)
    t = field_sqrt(s)
    if t is None:
        return []
    half = F(1, 2)
    mx, my = (a.x + b.x) * half, (a.y + b.y) * half
    wx, wy = -dv.y, dv.x
    out = []
    for sg in (1, -1):
        tt = t if sg > 0 else -t
        p = Point(mx + tt * wx, my + tt * wy)
        # EXACT re-verification; a non-unit candidate can never escape.
        if p.is_unit_from(a) and p.is_unit_from(b):
            out.append(p)
    return dedup_points(out)
