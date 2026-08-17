"""Hardened-stack basin hop with two-tier acceptance.

Two efficiency findings from earlier passes are applied here:

1. NO DETECTION IN THE LOOP. The pool is built once with the CERTIFIED
   (float-free) detector. Every candidate subset is then an induced subgraph, and
   its edge set is the pool's edges restricted to the subset - an identity, not a
   measurement. That is 4480x faster than re-detecting per candidate.

2. TWO-TIER ACCEPTANCE. A full deletion pass costs ~|S| solver calls (minutes).
   Instead, each perturbation is first triaged by UNSAT-core extraction, which
   costs a handful of calls. Only perturbations whose core already beats the
   incumbent get the expensive full pass. Because the core filter is a heuristic
   and could systematically mislead, one attempt in FORCE_FULL is given a full
   pass regardless, and both counts are logged so the filter's hit rate stays
   auditable rather than assumed.

   MEASURED RESULT: the core filter does NOT discriminate. Over the first six full
   passes, ZERO cores beat the incumbent and every full pass was a forced one -
   CaDiCaL's assumption core returns nearly all the assumptions it was given (518
   out of 510+8, 537 out of 510+38), so it barely reduces at all. Gating full
   passes at 1-in-12 was therefore discarding 11 of every 12 informative samples in
   exchange for no signal. HN_FORCE_FULL now defaults to 1, so every perturbation
   gets a real pass. The triage is kept only because it is nearly free and does
   cheaply reject a candidate that turns out to be colourable.

Soundness is unchanged. Search-time solver answers steer the search only; any
improvement is re-derived from exact coordinates and re-proved by
verify_candidate.py before it may be called a result.
"""
import json
import multiprocessing as mp
import os
import random
import sys
import time
from fractions import Fraction

sys.path.insert(0, "/home/user/CustomLLM/src")

from hn.field import MultiQuadField
from hn.graph import UDGraph
from hn.mathematica import load_vtx
from hn.minimizer import MUSReducer, restrict
from hn.point import Point

OUT = "/home/user/CustomLLM/catalog/search6.jsonl"
FORCE_FULL = int(os.environ.get("HN_FORCE_FULL", "1"))


def log(rec):
    with open(OUT, "a") as fh:
        fh.write(json.dumps(rec) + "\n")
        fh.flush()


def load_pool(path):
    d = json.load(open(path))
    F = MultiQuadField(tuple(d["field"]))
    pts = [
        Point(F.elem([Fraction(a, b) for a, b in p["x"]]),
              F.elem([Fraction(a, b) for a, b in p["y"]]))
        for p in d["points"]
    ]
    return pts, F


def core_triage(pool_adj, cand):
    """Cheap: UNSAT-core fixpoint on the induced subgraph. Returns pool indices."""
    sub = restrict(pool_adj, cand)
    R = MUSReducer(sub, 4)
    try:
        if not R.is_unsat(list(range(sub.n))):
            return None, R.calls
        keep = R.core_reduce(list(range(sub.n)))
        return [sub.index[i] for i in keep], R.calls
    finally:
        R.close()


def full_pass(pool_adj, cand, rng, priority, passes=3):
    """Expensive: deletion MUS to fixpoint, incumbent vertices tried first."""
    cur = sorted(cand)
    calls = 0
    for _ in range(passes):
        sub = restrict(pool_adj, cur)
        R = MUSReducer(sub, 4)
        try:
            if not R.is_unsat(list(range(sub.n))):
                return None, calls + R.calls
            keep = R.core_reduce(list(range(sub.n)))
            hi = [i for i in keep if sub.index[i] in priority]
            lo = [i for i in keep if sub.index[i] not in priority]
            rng.shuffle(hi)
            rng.shuffle(lo)
            keep = R.deletion_mus(keep, order=hi + lo)
            new = sorted(sub.index[i] for i in keep)
            calls += R.calls
        finally:
            R.close()
        if len(new) == len(cur):
            return new, calls
        cur = new
    return cur, calls


def worker(a):
    pool_path, seed, total = a
    pts, F = load_pool(pool_path)
    pool = UDGraph(pts, lineage={"op": "pool", "src": pool_path})
    padj = pool.adj
    key2i = {p.key(): i for i, p in enumerate(pool.points)}
    spts, _ = load_vtx("/home/user/CustomLLM/data/CNP-SAT/vtx/510.vtx", field=F)
    if any(p.key() not in key2i for p in spts):
        return {"seed": seed, "status": "pool missing 510 members"}
    B = sorted(key2i[p.key()] for p in spts)
    name = os.path.basename(pool_path)
    rng = random.Random(seed)
    t0 = time.time()
    best = list(B)
    log({"pool": name, "seed": seed, "iter": -1, "n": len(best),
         "pool_n": pool.n, "pool_m": pool.m})
    it = triaged = fulls = improved = 0
    calls = 0
    core_beat = 0
    while time.time() - t0 < total:
        it += 1
        bs = set(best)
        cnt = {}
        for v in range(pool.n):
            if v in bs:
                continue
            c = sum(1 for u in padj[v] if u in bs)
            if c >= 2:
                cnt[v] = c
        if not cnt:
            break
        cands = list(cnt)
        w = [cnt[v] ** 3 for v in cands]
        nadd = rng.randint(3, min(45, len(cands)))
        added = set()
        for _ in range(nadd * 5):
            if len(added) >= nadd:
                break
            added.add(rng.choices(cands, weights=w, k=1)[0])
        S = sorted(bs | added)

        triaged += 1
        core, c1 = core_triage(padj, S)
        calls += c1
        if core is None:
            continue
        promising = len(core) < len(best)
        if promising:
            core_beat += 1
        forced = (it % FORCE_FULL == 0)
        if not (promising or forced):
            continue

        fulls += 1
        res, c2 = full_pass(padj, core if promising else S, rng, bs)
        calls += c2
        if res is None:
            continue
        log({"pool": name, "seed": seed, "iter": it, "added": len(added),
             "core_n": len(core), "result_n": len(res), "best_n": len(best),
             "via": "core" if promising else "forced",
             "elapsed": round(time.time() - t0, 1)})
        if len(res) < len(best):
            best = res
            improved += 1
            log({"pool": name, "seed": seed, "n": len(best), "iter": it,
                 "IMPROVED": True, "vertices": sorted(best),
                 "pool_src": pool_path, "elapsed": round(time.time() - t0, 1)})
    return {"pool": name, "seed": seed, "n": len(best), "iters": it,
            "triaged": triaged, "core_beat": core_beat, "full_passes": fulls,
            "improved": improved, "calls": calls,
            "wall": round(time.time() - t0, 1)}


if __name__ == "__main__":
    pools = os.environ.get("HN_POOLS", ",".join([
        "data/pools/P3_nc510_deg3.json",
        "data/pools/P3_ncD6_deg3.json",
        "data/pools/P5a_super_510.json",
        "data/pools/P1d_510_rot_L2.json",
    ])).split(",")
    NW = int(os.environ.get("HN_WORKERS", "4"))
    T = float(os.environ.get("HN_TOTAL", "1500"))
    base = int(os.environ.get("HN_SEEDBASE", "300000"))
    R = int(os.environ.get("HN_ROUNDS", "6"))
    best = 10 ** 9
    with mp.Pool(NW) as P:
        for rd in range(R):
            args = [(pools[(rd * NW + i) % len(pools)], base + rd * NW + i, T)
                    for i in range(NW)]
            for rec in P.imap_unordered(worker, args):
                if rec.get("n") and rec["n"] < best:
                    best = rec["n"]
                print(f"rd{rd} {rec.get('pool')} seed={rec['seed']} n={rec.get('n')} "
                      f"triaged={rec.get('triaged')} core_beat={rec.get('core_beat')} "
                      f"full={rec.get('full_passes')} imp={rec.get('improved')} "
                      f"calls={rec.get('calls')} wall={rec.get('wall')} BEST={best}",
                      flush=True)
    print("DONE best=", best, flush=True)
