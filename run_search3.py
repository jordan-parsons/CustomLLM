"""Basin-hopping minimisation with SMALL encodings.

Lesson from pass 1: solving the 2306-vertex pool encoding under ~2300 assumption
literals is roughly 50x slower per call than the 510-vertex encoding, which ran
at 0.09s/call. So never encode the pool. For every candidate vertex set, build a
FRESH induced UDGraph and minimise that; encodings stay ~500-600 vertices.

Loop per worker:
  1. incumbent B (start: one of the 9 published 5-chromatic graphs), MUS-reduced
  2. inject a few ambient pool points touching >= 2 vertices of B
  3. build the induced graph on B + added, randomised deletion MUS to fixpoint
  4. keep it if strictly smaller than |B|

Search-time solver answers steer the search ONLY. Every improvement is logged
with its exact pool vertex indices so verify_candidate.py can certify it
independently with a DRAT proof and a checker verdict.
"""
import json
import multiprocessing as mp
import os
import random
import sys
import time

sys.path.insert(0, "/home/user/CustomLLM/src")

from hn.field import MultiQuadField
from hn.graph import UDGraph
from hn.mathematica import load_vtx
from hn.minimizer import MUSReducer

OUT = "/home/user/CustomLLM/catalog/search3.jsonl"
NAMES = ["510", "517", "529", "553", "610", "633", "803", "826", "874"]


def log(rec):
    with open(OUT, "a") as fh:
        fh.write(json.dumps(rec) + "\n")
        fh.flush()


def minimise_small(pool, idxs, rng, passes=4, priority=None):
    """Build a fresh small induced graph on idxs and MUS-reduce to fixpoint.

    `priority` is a set of pool indices to attempt deleting FIRST. This matters
    enormously for basin hopping: the incumbent B is vertex-critical, so if the
    deletion order is uniform over B + added, the few added points get deleted
    early and the pass collapses straight back to B. Trying B's own vertices
    first keeps the added constraints in play, which is the only way an incumbent
    vertex can be revealed as redundant.
    """
    cur = list(idxs)
    for _ in range(passes):
        sub = UDGraph([pool.points[i] for i in cur], lineage={"op": "induced"})
        R = MUSReducer(sub, 4)
        try:
            if not R.is_unsat(list(range(sub.n))):
                return None
            keep = R.core_reduce(list(range(sub.n)))
            order = None
            if priority:
                hi = [i for i in keep if cur[i] in priority]
                lo = [i for i in keep if cur[i] not in priority]
                rng.shuffle(hi)
                rng.shuffle(lo)
                order = hi + lo
            keep = R.deletion_mus(keep, order=order, rng=rng)
        finally:
            R.close()
        new = [cur[i] for i in sorted(keep)]
        if len(new) == len(cur):
            return new
        cur = new
    return cur


def worker(a):
    blob, gens, seed, total, start_name = a
    from fractions import Fraction

    from hn.point import Point

    F = MultiQuadField(tuple(gens))
    pts = [
        Point(F.elem([Fraction(x, y) for x, y in xs]),
              F.elem([Fraction(x, y) for x, y in ys]))
        for xs, ys in blob
    ]
    pool = UDGraph(pts, lineage={"op": "pool"})
    key2i = {p.key(): i for i, p in enumerate(pool.points)}
    spts, _ = load_vtx(f"/home/user/CustomLLM/data/CNP-SAT/vtx/{start_name}.vtx", field=F)
    B = sorted(key2i[p.key()] for p in spts)
    rng = random.Random(seed)
    t0 = time.time()
    B = minimise_small(pool, B, rng)
    if B is None:
        return {"seed": seed, "status": "start_colourable"}
    best = list(B)
    log({"seed": seed, "start": start_name, "n": len(best), "iter": -1,
         "vertices": sorted(best)})
    it = 0
    improved = 0
    while time.time() - t0 < total:
        it += 1
        bs = set(best)
        cnt = {}
        for v in range(pool.n):
            if v in bs:
                continue
            c = sum(1 for u in pool.adj[v] if u in bs)
            if c >= 2:
                cnt[v] = c
        if not cnt:
            break
        cands = list(cnt)
        w = [cnt[v] ** 2 for v in cands]
        nadd = rng.randint(4, min(60, len(cands)))
        added = set()
        for _ in range(nadd * 5):
            if len(added) >= nadd:
                break
            added.add(rng.choices(cands, weights=w, k=1)[0])
        res = minimise_small(pool, sorted(bs | added), rng, priority=set(bs))
        if res is None:
            continue
        if len(res) < len(best):
            best = res
            improved += 1
            log({"seed": seed, "start": start_name, "n": len(best), "iter": it,
                 "added": len(added), "IMPROVED": True, "vertices": sorted(best),
                 "elapsed": round(time.time() - t0, 1)})
    return {"seed": seed, "start": start_name, "n": len(best), "iters": it,
            "improved": improved, "wall": round(time.time() - t0, 1)}


if __name__ == "__main__":
    F = MultiQuadField((3, 5, 11))
    allk = {}
    for nm in NAMES:
        p, _ = load_vtx(f"/home/user/CustomLLM/data/CNP-SAT/vtx/{nm}.vtx", field=F)
        for q in p:
            allk[q.key()] = q
    g = UDGraph(list(allk.values()), lineage={"op": "union"})
    print(f"pool n={g.n} m={g.m}", flush=True)
    blob = [([[c.numerator, c.denominator] for c in q.x.coeffs],
             [[c.numerator, c.denominator] for c in q.y.coeffs]) for q in g.points]
    NW = int(os.environ.get("HN_WORKERS", "4"))
    T = float(os.environ.get("HN_TOTAL", "1200"))
    base = int(os.environ.get("HN_SEEDBASE", "9000"))
    R = int(os.environ.get("HN_ROUNDS", "6"))
    starts = os.environ.get("HN_STARTS", "510,517,529,553").split(",")
    best = 10 ** 9
    with mp.Pool(NW) as P:
        for rd in range(R):
            args = [(blob, (3, 5, 11), base + rd * NW + i, T,
                     starts[(rd * NW + i) % len(starts)]) for i in range(NW)]
            for rec in P.imap_unordered(worker, args):
                if rec.get("n") and rec["n"] < best:
                    best = rec["n"]
                print(f"rd{rd} seed={rec['seed']} start={rec.get('start')} "
                      f"n={rec.get('n')} iters={rec.get('iters')} "
                      f"improved={rec.get('improved')} wall={rec.get('wall')} "
                      f"BEST={best}", flush=True)
    print("DONE best=", best, flush=True)
