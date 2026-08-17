"""Unit-distance edge detection.

Contract
--------
Float is used ONLY to prune candidate pairs. Every pair that survives the prune
is confirmed by exact arithmetic in the number field, and only exactly-confirmed
pairs enter the edge set. `detect_edges` and `detect_edges_bruteforce_exact`
must agree on every input; the test suite enforces that.

The prune window is deliberately enormous relative to double-precision error
(1e-6 on squared distance vs ~1e-15 achievable error on these coordinate
magnitudes) so that a false negative is not credible. `audit_prune_margin`
reports the worst-case observed slack so the assumption stays measurable rather
than assumed.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Dict, List, Sequence, Set, Tuple

from .point import Point

# Squared-distance window for the float prefilter. Pairs outside this window are
# discarded without exact confirmation; pairs inside are exactly confirmed.
PRUNE_WINDOW = 1e-6


def detect_edges(
    points: Sequence[Point], window: float = PRUNE_WINDOW
) -> List[Tuple[int, int]]:
    """Return all exactly-unit-distance index pairs, using a grid prefilter."""
    n = len(points)
    approx = [p.approx() for p in points]
    # Bucket at cell size 1 so unit-distance pairs are always in adjacent cells.
    buckets: Dict[Tuple[int, int], List[int]] = defaultdict(list)
    for i, (x, y) in enumerate(approx):
        buckets[(math.floor(x), math.floor(y))].append(i)

    edges: List[Tuple[int, int]] = []
    seen: Set[Tuple[int, int]] = set()
    for (cx, cy), idxs in buckets.items():
        neigh: List[int] = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                neigh.extend(buckets.get((cx + dx, cy + dy), ()))
        for i in idxs:
            xi, yi = approx[i]
            for j in neigh:
                if j <= i:
                    continue
                xj, yj = approx[j]
                d2 = (xi - xj) ** 2 + (yi - yj) ** 2
                if abs(d2 - 1.0) > window:
                    continue  # FILTER ONLY
                key = (i, j)
                if key in seen:
                    continue
                seen.add(key)
                # EXACT CONFIRMATION - this is what decides the edge.
                if points[i].is_unit_from(points[j]):
                    edges.append(key)
    edges.sort()
    return edges


def detect_edges_bruteforce_exact(points: Sequence[Point]) -> List[Tuple[int, int]]:
    """Reference detector: exact arithmetic on all O(n^2) pairs. No filtering."""
    n = len(points)
    edges = []
    for i in range(n):
        pi = points[i]
        for j in range(i + 1, n):
            if pi.is_unit_from(points[j]):
                edges.append((i, j))
    return edges


def audit_prune_margin(points: Sequence[Point]) -> Dict[str, float]:
    """Measure how close the float prefilter came to making a wrong call.

    Returns the largest |d^2 - 1| among pairs that ARE exactly unit distance
    (must stay far below PRUNE_WINDOW, else the filter could drop a real edge),
    and the smallest |d^2 - 1| among pairs that are NOT unit distance but passed
    the window (shows how much exact confirmation is actually doing).
    """
    approx = [p.approx() for p in points]
    worst_true = 0.0
    closest_false = float("inf")
    n = len(points)
    for i in range(n):
        xi, yi = approx[i]
        for j in range(i + 1, n):
            xj, yj = approx[j]
            d2 = (xi - xj) ** 2 + (yi - yj) ** 2
            err = abs(d2 - 1.0)
            if points[i].is_unit_from(points[j]):
                worst_true = max(worst_true, err)
            elif err <= PRUNE_WINDOW:
                closest_false = min(closest_false, err)
    return {
        "max_float_error_on_true_edges": worst_true,
        "min_float_error_on_non_edges_passing_window": closest_false,
        "prune_window": PRUNE_WINDOW,
    }


def verify_edges_exact(
    points: Sequence[Point], edges: Sequence[Tuple[int, int]]
) -> Tuple[bool, List[Tuple[int, int]]]:
    """Independently re-confirm every claimed edge is EXACTLY unit distance.

    This is the adversary's check. Returns (all_ok, list_of_bad_edges).
    """
    bad = []
    for (i, j) in edges:
        if i == j:
            bad.append((i, j))
            continue
        if not points[i].is_unit_from(points[j]):
            bad.append((i, j))
    return (len(bad) == 0, bad)


# ---------------------------------------------------------------------------
# CERTIFIED detector (ADVERSARY-2 FINDINGS A1-A4)
# ---------------------------------------------------------------------------
# A2 demonstrated that the float prefilter above can MISS an exactly-unit edge:
# with coefficients around 9.5e9 the pair is lost even though every coordinate
# satisfies |x| < 1.26, and the grid bucketing breaks at coefficient scale 2^25
# because math.floor is applied to a float (fl(x)=4.99999999627471 buckets to 4
# while its true value buckets to 5). Composing the spindle rotation grows
# denominators like 6^n, which passes 1e12 by n=25, so this is reachable by
# ordinary construction moves rather than only by adversarial input.
#
# The fix removes float from the path entirely. Every coordinate gets a CERTIFIED
# rational enclosure [lo, hi] built from integer square roots, so:
#   * bucketing uses floor(lo) on an exact rational. Two points with |dx| <= 1
#     can differ by at most 2 buckets for ANY enclosure width <= 1, so scanning a
#     +-2 neighbourhood is unconditionally safe - correctness does not depend on
#     the precision chosen.
#   * a pair is discarded only if the certified interval for its squared distance
#     provably EXCLUDES 1. Precision therefore affects speed, never correctness.
# Surviving pairs are still confirmed by exact field arithmetic.

from fractions import Fraction as _F
from math import isqrt as _isqrt

CERT_PREC = 10 ** 60


def _radical_bounds(field, prec: int = CERT_PREC):
    """Certified rational bounds for sqrt of each basis radical."""
    out = {}
    for mask in range(field.dim):
        r = 1
        for i in range(field.k):
            if mask >> i & 1:
                r *= field.gens[i]
        if r == 1:
            out[mask] = (_F(1), _F(1))
        else:
            root = _isqrt(r * prec * prec)
            out[mask] = (_F(root, prec), _F(root + 1, prec))
    return out


def certified_bounds(elem, rb):
    """Certified [lo, hi] with lo <= exact value of `elem` <= hi."""
    lo = _F(0)
    hi = _F(0)
    for s, c in enumerate(elem.coeffs):
        if c == 0:
            continue
        rlo, rhi = rb[s]
        if c > 0:
            lo += c * rlo
            hi += c * rhi
        else:
            lo += c * rhi
            hi += c * rlo
    return lo, hi


def _sq_interval(a: _F, b: _F):
    """Square of the interval [a, b]."""
    if a >= 0:
        return a * a, b * b
    if b <= 0:
        return b * b, a * a
    m = a * a if -a > b else b * b
    return _F(0), m


def detect_edges_certified(points, prec: int = CERT_PREC):
    """Exact unit-distance detection with a CERTIFIED (float-free) prefilter."""
    n = len(points)
    if n == 0:
        return []
    rb = _radical_bounds(points[0].field, prec)
    bounds = []
    for p in points:
        xlo, xhi = certified_bounds(p.x, rb)
        ylo, yhi = certified_bounds(p.y, rb)
        bounds.append((xlo, xhi, ylo, yhi))

    buckets = defaultdict(list)
    for i, (xlo, _, ylo, _) in enumerate(bounds):
        # exact rational floor - no float, no math.floor
        buckets[(xlo.numerator // xlo.denominator,
                 ylo.numerator // ylo.denominator)].append(i)

    edges = []
    seen = set()
    one = _F(1)
    for (cx, cy), idxs in buckets.items():
        neigh = []
        for dx in (-2, -1, 0, 1, 2):
            for dy in (-2, -1, 0, 1, 2):
                neigh.extend(buckets.get((cx + dx, cy + dy), ()))
        for i in idxs:
            xilo, xihi, yilo, yihi = bounds[i]
            for j in neigh:
                if j <= i or (i, j) in seen:
                    continue
                xjlo, xjhi, yjlo, yjhi = bounds[j]
                dxlo, dxhi = xilo - xjhi, xihi - xjlo
                dylo, dyhi = yilo - yjhi, yihi - yjlo
                sxlo, sxhi = _sq_interval(dxlo, dxhi)
                sylo, syhi = _sq_interval(dylo, dyhi)
                # discard ONLY if 1 is provably outside [lo, hi]
                if (sxlo + sylo) > one or (sxhi + syhi) < one:
                    continue
                seen.add((i, j))
                if points[i].is_unit_from(points[j]):
                    edges.append((i, j))
    edges.sort()
    return edges
