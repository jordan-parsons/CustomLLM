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
