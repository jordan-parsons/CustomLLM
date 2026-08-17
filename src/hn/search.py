"""Parallel randomised MUS search over an ambient point pool.

Each worker repeatedly:
  1. core_reduce   - cheap UNSAT-core fixpoint, big early wins
  2. batch descent - try deleting random blocks; restore on SAT, shrink block
  3. deletion MUS  - single-vertex fixpoint pass in a random order

Different seeds give different local minima. Results are appended as JSON lines
so a monitor can track the running best without touching worker state.

Search-time solver answers steer the search only. Anything that beats the
incumbent is re-solved by the oracle with DRAT logging and drat-trim
verification before it is allowed to be called a result.
"""

from __future__ import annotations

import json
import os
import random
import time
from typing import Dict, List, Optional, Sequence

from .graph import UDGraph
from .minimizer import MUSReducer


def batch_descent(
    R: MUSReducer,
    S: Sequence[int],
    rng: random.Random,
    start_block: int = 64,
    min_block: int = 1,
    time_budget: Optional[float] = None,
    t_start: Optional[float] = None,
) -> List[int]:
    """Delete random blocks; on SAT restore and halve the block size."""
    cur = list(S)
    block = max(min_block, min(start_block, len(cur) // 4 or 1))
    while block >= min_block:
        if time_budget and t_start and (time.time() - t_start) > time_budget:
            break
        progressed = False
        order = list(cur)
        rng.shuffle(order)
        i = 0
        while i < len(order):
            if time_budget and t_start and (time.time() - t_start) > time_budget:
                break
            drop = set(order[i : i + block])
            i += block
            drop &= set(cur)
            if not drop or len(drop) >= len(cur):
                continue
            trial = [v for v in cur if v not in drop]
            if R.is_unsat(trial):
                cur = trial
                progressed = True
        if not progressed:
            block //= 2
        # else keep the same block size and go again
    return cur


def one_run(
    g: UDGraph,
    k: int,
    seed: int,
    time_budget: float = 900.0,
    start_subset: Optional[Sequence[int]] = None,
) -> Dict:
    rng = random.Random(seed)
    t0 = time.time()
    R = MUSReducer(g, k)
    try:
        S = list(start_subset) if start_subset is not None else list(range(g.n))
        if not R.is_unsat(S):
            return {"seed": seed, "status": "start_colourable", "n": len(S)}
        S = R.core_reduce(S)
        after_core = len(S)
        S = batch_descent(R, S, rng, time_budget=time_budget, t_start=t0)
        after_batch = len(S)
        # final single-vertex fixpoint
        for _ in range(4):
            before = len(S)
            S = R.deletion_mus(S, rng=rng)
            if len(S) == before:
                break
            if time.time() - t0 > time_budget * 1.5:
                break
        return {
            "seed": seed,
            "status": "ok",
            "n": len(S),
            "after_core": after_core,
            "after_batch": after_batch,
            "calls": R.calls,
            "wall": round(time.time() - t0, 1),
            "vertices": sorted(S),
        }
    finally:
        R.close()


def worker(args):
    (points_blob, field_gens, k, seed, budget, out_path, start_subset) = args
    from fractions import Fraction
    from .field import MultiQuadField
    from .point import Point

    F = MultiQuadField(tuple(field_gens))
    pts = [
        Point(F.elem([Fraction(a, b) for a, b in xs]), F.elem([Fraction(a, b) for a, b in ys]))
        for xs, ys in points_blob
    ]
    g = UDGraph(pts, lineage={"op": "search_pool"})
    rec = one_run(g, k, seed, time_budget=budget, start_subset=start_subset)
    rec["pool_n"] = g.n
    with open(out_path, "a") as fh:
        fh.write(json.dumps(rec) + "\n")
        fh.flush()
    return {kk: vv for kk, vv in rec.items() if kk != "vertices"}


def blobify(g: UDGraph):
    return [
        (
            [[c.numerator, c.denominator] for c in p.x.coeffs],
            [[c.numerator, c.denominator] for c in p.y.coeffs],
        )
        for p in g.points
    ]
