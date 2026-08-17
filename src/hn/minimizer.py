"""Vertex-set minimisation via UNSAT cores and deletion-based MUS.

Encoding trick
--------------
Give each vertex v a *presence* literal p_v. The at-least-one-colour clause
becomes

    (x[v][0] v ... v x[v][k-1] v ~p_v)

Then solving under assumption p_v = true forces v to be coloured, and p_v = false
lets v stay entirely uncoloured. An uncoloured vertex satisfies every edge clause
it appears in vacuously (all its colour literals are false), so

    solve(assumptions = {p_v : v in S})  is UNSAT
      <=>  the induced subgraph G[S] is not k-colourable.

That equivalence is exact, which is what makes core extraction usable: the core
of an UNSAT call is a subset S' of S with G[S'] still not k-colourable.

Symmetry breaking is applied CONDITIONALLY as (~p_v v x[v][i]) so that deleting
a pinned vertex cannot introduce a spurious constraint. Pinning any clique of
present vertices to distinct colours is sound because colour classes are
interchangeable.

Search vs. claims
-----------------
Solver answers here are used to steer the SEARCH and are deliberately NOT
recorded as verdicts. Every graph this module reports is re-solved from scratch
by the oracle with DRAT proof logging and checker verification before it may be
called a result. If a search-time UNSAT were wrong, the final verified solve
would come back SAT and the claim would be rejected.
"""

from __future__ import annotations

import random
from typing import Dict, List, Optional, Sequence, Set, Tuple

from .cnf import find_clique_greedy, var
from .graph import UDGraph


def build_mus_encoding(
    g: UDGraph, k: int, break_symmetry: bool = True
) -> Tuple[List[List[int]], Dict[int, int], List[str]]:
    """Return (clauses, presence_literal_by_vertex, justifications)."""
    n = g.n
    base_vars = n * k
    pres = {v: base_vars + 1 + v for v in range(n)}
    clauses: List[List[int]] = []
    just: List[str] = []

    for v in range(n):
        clauses.append([var(v, c, k) for c in range(k)] + [-pres[v]])
    just.append(
        "relaxed at-least-one: (colours of v) v ~p_v. With p_v assumed true this "
        "is the standard ALO clause; with p_v false, v may stay uncoloured and "
        "then satisfies every edge clause vacuously, which is exactly deletion. "
        "So UNSAT under assumptions {p_v : v in S} iff G[S] is not k-colourable."
    )
    for (u, v) in g.edges:
        for c in range(k):
            clauses.append([-var(u, c, k), -var(v, c, k)])
    just.append("edge clauses unchanged; vacuous for uncoloured endpoints.")

    if break_symmetry:
        clique = find_clique_greedy(n, g.adj, min(k, 3))
        if len(clique) >= 2:
            for i, v in enumerate(clique):
                clauses.append([-pres[v], var(v, i, k)])
            just.append(
                f"conditional symmetry breaking on clique {clique}: (~p_v v x[v][i]). "
                "Sound because (a) it is inactive for deleted vertices, and (b) for "
                "any subset of a clique that is present, pinning those vertices to "
                "distinct colours only removes colour-permutation duplicates."
            )
    return clauses, pres, just


class MUSReducer:
    """Incremental reducer over one graph. Reuses a single solver instance."""

    def __init__(self, g: UDGraph, k: int, break_symmetry: bool = True,
                 solver_name: str = "cadical153"):
        from pysat.solvers import Solver

        self.g = g
        self.k = k
        self.clauses, self.pres, self.justifications = build_mus_encoding(
            g, k, break_symmetry
        )
        self.solver = Solver(name=solver_name, bootstrap_with=self.clauses)
        self.calls = 0

    def close(self):
        try:
            self.solver.delete()
        except Exception:
            pass

    def is_unsat(self, S: Sequence[int]) -> bool:
        self.calls += 1
        return not self.solver.solve(assumptions=[self.pres[v] for v in S])

    def core(self, S: Sequence[int]) -> Optional[List[int]]:
        """If G[S] is not k-colourable, return a core subset; else None."""
        self.calls += 1
        if self.solver.solve(assumptions=[self.pres[v] for v in S]):
            return None
        c = self.solver.get_core()
        if not c:
            return list(S)
        inv = {lit: v for v, lit in self.pres.items()}
        return sorted(inv[l] for l in c if l in inv)

    def core_reduce(self, S: Sequence[int], rounds: int = 8) -> List[int]:
        """Iterate core extraction to a fixpoint (cheap, big early wins)."""
        cur = sorted(S)
        for _ in range(rounds):
            c = self.core(cur)
            if c is None:
                return cur  # colourable: cannot reduce from here
            if len(c) >= len(cur):
                return cur
            cur = c
        return cur

    def deletion_mus(
        self,
        S: Sequence[int],
        order: Optional[Sequence[int]] = None,
        rng: Optional[random.Random] = None,
        progress=None,
    ) -> List[int]:
        """Classic deletion-based MUS: try dropping each vertex once, in `order`."""
        cur: List[int] = sorted(S)
        curset: Set[int] = set(cur)
        seq = list(order) if order is not None else list(cur)
        if order is None and rng is not None:
            rng.shuffle(seq)
        for idx, v in enumerate(seq):
            if v not in curset:
                continue
            trial = [u for u in cur if u != v]
            if not trial:
                continue
            if self.is_unsat(trial):
                cur = trial
                curset.discard(v)
                if progress:
                    progress(len(cur), v, True)
            elif progress:
                progress(len(cur), v, False)
        return cur

    def to_fixpoint(
        self, S: Sequence[int], rng: Optional[random.Random] = None,
        max_passes: int = 6, progress=None
    ) -> List[int]:
        cur = self.core_reduce(S)
        for _ in range(max_passes):
            before = len(cur)
            cur = self.deletion_mus(cur, rng=rng, progress=progress)
            cur = self.core_reduce(cur)
            if len(cur) == before:
                break
        return cur

    def critical_scan(self, S: Sequence[int]) -> Dict[int, bool]:
        """For each v in S, is G[S - v] still non-k-colourable?

        A vertex is 'critical' when removing it makes the graph k-colourable.
        If every vertex is critical, G[S] is vertex-critical and no single
        deletion can shrink it.
        """
        cur = sorted(S)
        out: Dict[int, bool] = {}
        for v in cur:
            trial = [u for u in cur if u != v]
            out[v] = self.is_unsat(trial)  # True => v is redundant, removable
        return out
