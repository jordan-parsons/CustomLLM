"""CNF encoding of k-colourability, with documented symmetry breaking.

Variable convention (fixed, documented, and relied on by the independent
checker in `modelcheck.py`):

    var(v, c) = v * k + c + 1       for v in [0, n), c in [0, k)

Base encoding (Sec. 5 of the spec):
  * at-least-one-colour per vertex
  * for each edge and colour, forbid both endpoints taking it
  * at-most-one-colour is OMITTED (any satisfying assignment still yields a
    proper colouring by choosing any single true colour per vertex, and every
    vertex has at least one true colour)

SOUNDNESS NOTES for every optional constraint are recorded in
`EncodingResult.justifications` and are copied verbatim into the catalog row.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Dict, List, Optional, Sequence, Tuple


def var(v: int, c: int, k: int) -> int:
    return v * k + c + 1


@dataclass
class EncodingResult:
    n_vars: int
    clauses: List[List[int]]
    k: int
    n: int
    justifications: List[str] = dc_field(default_factory=list)
    fixed: Dict[int, int] = dc_field(default_factory=dict)

    def to_dimacs(self) -> str:
        out = [f"p cnf {self.n_vars} {len(self.clauses)}"]
        out.extend(" ".join(map(str, cl)) + " 0" for cl in self.clauses)
        return "\n".join(out) + "\n"

    def write(self, path: str) -> str:
        with open(path, "w") as fh:
            fh.write(self.to_dimacs())
        return path


def find_clique_greedy(n: int, adj: Sequence[Sequence[int]], size: int) -> List[int]:
    """Find a clique of exactly `size` vertices, or return []. Exhaustive-ish
    greedy over vertices ordered by degree; adequate for triangles/K4 in UD graphs."""
    nbr = [set(a) for a in adj]
    order = sorted(range(n), key=lambda v: -len(nbr[v]))

    def extend(cur: List[int], cand: set) -> Optional[List[int]]:
        if len(cur) == size:
            return list(cur)
        if len(cur) + len(cand) < size:
            return None
        for v in sorted(cand, key=lambda v: -len(nbr[v])):
            res = extend(cur + [v], cand & nbr[v])
            if res is not None:
                return res
            cand = cand - {v}
        return None

    for v in order:
        res = extend([v], set(nbr[v]))
        if res:
            return res
    return []


def encode_coloring(
    n: int,
    edges: Sequence[Tuple[int, int]],
    k: int,
    adj: Optional[Sequence[Sequence[int]]] = None,
    break_symmetry: bool = True,
) -> EncodingResult:
    clauses: List[List[int]] = []
    just: List[str] = []

    for v in range(n):
        clauses.append([var(v, c, k) for c in range(k)])
    just.append(
        "at-least-one-colour per vertex: required for the encoding to express a "
        "total colouring. Sound by definition."
    )
    for (u, v) in edges:
        for c in range(k):
            clauses.append([-var(u, c, k), -var(v, c, k)])
    just.append(
        "edge constraints: for every exactly-confirmed unit-distance edge (u,v) "
        "and colour c, forbid both endpoints from taking c. Sound by definition "
        "of proper colouring."
    )
    just.append(
        "at-most-one-colour per vertex OMITTED. Sound: given any satisfying "
        "assignment, choose for each vertex one colour whose variable is true "
        "(exists by the ALO clause); no edge can then be monochromatic because "
        "the edge clauses forbid any shared true colour. So SAT of this "
        "encoding is equivalent to k-colourability, in both directions."
    )

    fixed: Dict[int, int] = {}
    if break_symmetry and adj is not None:
        clique = find_clique_greedy(n, adj, min(k, 3))
        if len(clique) >= 2:
            for i, v in enumerate(clique):
                clauses.append([var(v, i, k)])
                fixed[v] = i
            just.append(
                f"symmetry breaking: vertices {clique} form a clique of size "
                f"{len(clique)} (verified pairwise-adjacent in the exactly-derived "
                f"edge set); they are pinned to distinct colours 0..{len(clique)-1}. "
                "SOUND because the colour classes are interchangeable: any proper "
                "k-colouring can be composed with a permutation of colours sending "
                "the clique's colours to 0..len-1, and a clique forces its members "
                "to pairwise-distinct colours, so this eliminates only symmetric "
                "duplicates and preserves satisfiability in both directions."
            )
        else:
            just.append("symmetry breaking: no clique of size >= 2 found; skipped.")
    else:
        just.append("symmetry breaking: disabled for this encoding.")

    return EncodingResult(
        n_vars=n * k, clauses=clauses, k=k, n=n, justifications=just, fixed=fixed
    )


def verify_clique(clique: Sequence[int], edges: Sequence[Tuple[int, int]]) -> bool:
    """Independent confirmation that the symmetry-breaking clique really is one."""
    es = {(min(a, b), max(a, b)) for a, b in edges}
    for i in range(len(clique)):
        for j in range(i + 1, len(clique)):
            a, b = clique[i], clique[j]
            if (min(a, b), max(a, b)) not in es:
                return False
    return True
