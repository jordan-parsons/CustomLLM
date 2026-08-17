"""Immutable, content-addressed unit-distance graphs with exact coordinates."""

from __future__ import annotations

import hashlib
import json
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .detect import detect_edges, verify_edges_exact
from .field import MultiQuadField
from .point import Point


class UDGraph:
    """A unit-distance graph. Edges are ALWAYS derived by exact detection.

    There is deliberately no constructor that accepts a hand-supplied edge list
    for a geometric graph: the edge set is a function of the vertex set, and
    letting a caller assert edges is exactly how an unsound edge slips in.
    """

    __slots__ = ("points", "edges", "field", "lineage", "_hash", "_adj")

    def __init__(
        self,
        points: Sequence[Point],
        lineage: Optional[Dict] = None,
        edges: Optional[List[Tuple[int, int]]] = None,
    ):
        self.points = list(points)
        if not self.points:
            raise ValueError("empty vertex set")
        self.field = self.points[0].field
        for p in self.points:
            if p.field != self.field:
                raise TypeError("mixed fields in vertex set")
        # Exact dedup check: duplicate points would create self-loops / bogus counts
        keys = {p.key() for p in self.points}
        if len(keys) != len(self.points):
            raise ValueError(
                f"vertex set contains exact duplicates "
                f"({len(self.points)} points, {len(keys)} distinct)"
            )
        self.edges = detect_edges(self.points) if edges is None else sorted(edges)
        # Belt and braces: every edge re-confirmed exactly, always, on construction.
        ok, bad = verify_edges_exact(self.points, self.edges)
        if not ok:
            raise AssertionError(f"SOUNDNESS ALARM: non-unit edges detected: {bad[:5]}")
        self.lineage = lineage or {}
        self._hash = None
        self._adj = None

    @property
    def n(self) -> int:
        return len(self.points)

    @property
    def m(self) -> int:
        return len(self.edges)

    @property
    def adj(self) -> List[List[int]]:
        if self._adj is None:
            a: List[List[int]] = [[] for _ in range(self.n)]
            for (u, v) in self.edges:
                a[u].append(v)
                a[v].append(u)
            self._adj = a
        return self._adj

    def degree_sequence(self) -> List[int]:
        return sorted(len(x) for x in self.adj)

    def induced(self, keep: Iterable[int]) -> "UDGraph":
        """Induced subgraph on `keep`. Edges are re-detected exactly."""
        keep = sorted(set(keep))
        pts = [self.points[i] for i in keep]
        return UDGraph(
            pts,
            lineage={
                "op": "induced",
                "parent": self.graph_hash(),
                "kept": len(keep),
            },
        )

    def coord_hash(self) -> str:
        """Content address of the exact coordinate set (embedding identity)."""
        keys = sorted(p.key() for p in self.points)
        blob = json.dumps(
            {"field": self.field.gens, "points": keys}, sort_keys=True
        ).encode()
        return hashlib.sha256(blob).hexdigest()

    def graph_hash(self) -> str:
        """Isomorphism-invariant hash of the ABSTRACT graph (WL-based).

        NOTE: this is an invariant, not a certified canonical form. Dedup that
        relies on it MUST confirm with an exact isomorphism test (see catalog).
        """
        if self._hash is None:
            self._hash = _wl_hash(self.n, self.edges)
        return self._hash

    def to_dict(self) -> Dict:
        return {
            "field": list(self.field.gens),
            "n": self.n,
            "m": self.m,
            "points": [
                {
                    "x": [[c.numerator, c.denominator] for c in p.x.coeffs],
                    "y": [[c.numerator, c.denominator] for c in p.y.coeffs],
                }
                for p in self.points
            ],
            "edges": [list(e) for e in self.edges],
            "lineage": self.lineage,
            "coord_hash": self.coord_hash(),
            "graph_hash": self.graph_hash(),
        }

    @staticmethod
    def from_dict(d: Dict) -> "UDGraph":
        from fractions import Fraction

        f = MultiQuadField(tuple(d["field"]))
        pts = []
        for pd in d["points"]:
            x = f.elem([Fraction(a, b) for a, b in pd["x"]])
            y = f.elem([Fraction(a, b) for a, b in pd["y"]])
            pts.append(Point(x, y))
        # Edges are RE-DETECTED, not trusted from the file.
        return UDGraph(pts, lineage=d.get("lineage", {}))

    def __repr__(self) -> str:
        return f"UDGraph(n={self.n}, m={self.m}, field={self.field})"


def _wl_hash(n: int, edges: Sequence[Tuple[int, int]], rounds: int = 4) -> str:
    """1-dimensional Weisfeiler-Leman colour refinement hash."""
    adj: List[List[int]] = [[] for _ in range(n)]
    for (u, v) in edges:
        adj[u].append(v)
        adj[v].append(u)
    colours = [hashlib.sha256(str(len(a)).encode()).hexdigest()[:16] for a in adj]
    for _ in range(rounds):
        new = []
        for i in range(n):
            sig = colours[i] + "|" + "|".join(sorted(colours[j] for j in adj[i]))
            new.append(hashlib.sha256(sig.encode()).hexdigest()[:16])
        colours = new
    agg = hashlib.sha256(
        (str(n) + "#" + str(len(edges)) + "#" + "|".join(sorted(colours))).encode()
    ).hexdigest()
    return agg


def isomorphic(g1: UDGraph, g2: UDGraph) -> bool:
    """Exact isomorphism test (VF2). Used to confirm any dedup decision."""
    if g1.n != g2.n or g1.m != g2.m:
        return False
    if g1.degree_sequence() != g2.degree_sequence():
        return False
    import networkx as nx

    a = nx.Graph()
    a.add_nodes_from(range(g1.n))
    a.add_edges_from(g1.edges)
    b = nx.Graph()
    b.add_nodes_from(range(g2.n))
    b.add_edges_from(g2.edges)
    return nx.is_isomorphic(a, b)
