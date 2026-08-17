"""Independent model checker.

Deliberately written without importing anything from `cnf.py`. It re-derives the
variable convention from its own documented formula and re-derives the edge set
from the exact coordinates, so a bug in the encoder cannot be masked by the same
bug in the checker.

Convention (independently restated): variable index for vertex v, colour c, with
k colours, is v*k + c + 1. Vertices and colours are 0-based.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from .point import Point


def decode_model(model: Sequence[int], n: int, k: int) -> List[Optional[int]]:
    """Pick, for each vertex, the lowest colour whose variable is positive."""
    true_vars = set(l for l in model if l > 0)
    out: List[Optional[int]] = []
    for v in range(n):
        chosen = None
        for c in range(k):
            if (v * k + c + 1) in true_vars:
                chosen = c
                break
        out.append(chosen)
    return out


def check_coloring_against_points(
    points: Sequence[Point], model: Sequence[int], k: int
) -> Dict:
    """Full independent verification of a claimed k-colouring.

    Re-detects unit distances from exact coordinates by brute-force exact
    arithmetic (O(n^2), no float filter at all), then checks the colouring.
    """
    n = len(points)
    colors = decode_model(model, n, k)
    problems: List[str] = []

    uncolored = [v for v in range(n) if colors[v] is None]
    if uncolored:
        problems.append(f"{len(uncolored)} vertices have no true colour variable")

    bad_edges: List[Tuple[int, int]] = []
    edge_count = 0
    for i in range(n):
        pi = points[i]
        for j in range(i + 1, n):
            # exact unit-distance test, brute force, no tolerance anywhere
            dx = pi.x - points[j].x
            dy = pi.y - points[j].y
            if (dx * dx + dy * dy).equals_rational(1):
                edge_count += 1
                if colors[i] is not None and colors[i] == colors[j]:
                    bad_edges.append((i, j))
    if bad_edges:
        problems.append(f"{len(bad_edges)} monochromatic unit-distance edges")

    used = sorted({c for c in colors if c is not None})
    if used and (used[0] < 0 or used[-1] >= k):
        problems.append(f"colour out of range: {used}")

    return {
        "ok": not problems,
        "n": n,
        "edges_found_exactly": edge_count,
        "k": k,
        "colors_used": len(used),
        "bad_edges": bad_edges[:20],
        "problems": problems,
    }


def check_coloring_against_edges(
    n: int, edges: Sequence[Tuple[int, int]], model: Sequence[int], k: int
) -> Dict:
    """Same check but against a supplied edge list (for non-geometric graphs)."""
    colors = decode_model(model, n, k)
    bad = [
        (u, v)
        for (u, v) in edges
        if colors[u] is not None and colors[u] == colors[v]
    ]
    uncolored = [v for v in range(n) if colors[v] is None]
    return {
        "ok": not bad and not uncolored,
        "n": n,
        "m": len(edges),
        "bad_edges": bad[:20],
        "uncolored": len(uncolored),
    }
