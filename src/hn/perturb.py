"""Basin-hopping minimisation: escape a vertex-critical local minimum.

The 510-vertex graph is vertex-critical, so pure deletion is stuck. The standard
escape is "add then remove": inject a few ambient points, which can create new
constraints that make several *other* vertices redundant, then re-minimise. If
adding a points lets you delete a+d, you net -d.

Requires an ambient pool strictly larger than the incumbent's vertex set, since
by criticality no subset of the incumbent works.

All solver answers here steer the search only. Any incumbent improvement is
handed to verify_candidate.py for the full proof-backed evidence chain.
"""

from __future__ import annotations

import json
import random
import time
from typing import Dict, List, Optional, Sequence, Set

from .graph import UDGraph
from .minimizer import MUSReducer


def neighbours_in_pool(g: UDGraph, subset: Sequence[int]) -> Dict[int, int]:
    """For each pool vertex outside `subset`, how many subset vertices it touches."""
    sub = set(subset)
    counts: Dict[int, int] = {}
    for v in range(g.n):
        if v in sub:
            continue
        c = sum(1 for u in g.adj[v] if u in sub)
        if c:
            counts[v] = c
    return counts


def basin_hop(
    g: UDGraph,
    k: int,
    incumbent: Sequence[int],
    seed: int = 0,
    iters: int = 200,
    add_min: int = 1,
    add_max: int = 12,
    time_budget: float = 1800.0,
    min_touch: int = 2,
    log_path: Optional[str] = None,
) -> Dict:
    """Repeatedly inject ambient points and re-minimise, keeping improvements."""
    rng = random.Random(seed)
    t0 = time.time()
    R = MUSReducer(g, k)
    best = sorted(incumbent)
    history = []
    try:
        if not R.is_unsat(best):
            return {"status": "incumbent_colourable", "seed": seed}
        for it in range(iters):
            if time.time() - t0 > time_budget:
                break
            cand_pool = neighbours_in_pool(g, best)
            cands = [v for v, c in cand_pool.items() if c >= min_touch]
            if not cands:
                history.append({"iter": it, "note": "no ambient candidates"})
                break
            # weight by how many incumbent vertices they touch
            weights = [cand_pool[v] ** 2 for v in cands]
            nadd = rng.randint(add_min, min(add_max, len(cands)))
            added: Set[int] = set()
            for _ in range(nadd * 4):
                if len(added) >= nadd:
                    break
                pick = rng.choices(cands, weights=weights, k=1)[0]
                added.add(pick)
            S = sorted(set(best) | added)
            if not R.is_unsat(S):
                continue  # adding cannot break UNSAT, but be safe
            S = R.core_reduce(S)
            for _ in range(3):
                before = len(S)
                S = R.deletion_mus(S, rng=rng)
                if len(S) == before:
                    break
            rec = {
                "iter": it, "added": sorted(added), "result_n": len(S),
                "best_n": len(best), "elapsed": round(time.time() - t0, 1),
            }
            if len(S) < len(best):
                rec["IMPROVED"] = True
                best = sorted(S)
                rec["best_n"] = len(best)
                if log_path:
                    with open(log_path, "a") as fh:
                        fh.write(json.dumps({"seed": seed, "n": len(best),
                                             "vertices": best}) + "\n")
                        fh.flush()
            history.append(rec)
        return {
            "status": "ok", "seed": seed, "best_n": len(best),
            "best_vertices": best, "calls": R.calls,
            "wall": round(time.time() - t0, 1), "history": history[-40:],
        }
    finally:
        R.close()


def worker(args):
    (blob, gens, k, incumbent, seed, iters, budget, log_path, min_touch) = args
    from fractions import Fraction

    from .field import MultiQuadField
    from .point import Point

    F = MultiQuadField(tuple(gens))
    pts = [
        Point(F.elem([Fraction(a, b) for a, b in xs]),
              F.elem([Fraction(a, b) for a, b in ys]))
        for xs, ys in blob
    ]
    g = UDGraph(pts, lineage={"op": "perturb_pool"})
    out = basin_hop(g, k, incumbent, seed=seed, iters=iters,
                    time_budget=budget, log_path=log_path, min_touch=min_touch)
    return {kk: vv for kk, vv in out.items() if kk not in ("best_vertices", "history")}
