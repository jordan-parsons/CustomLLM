"""Basin hop over a TARGETED ambient pool from the constructor.

Pass-2 conclusion: the published corpus is uniformly vertex-critical, so the
ambient set must grow before minimisation can win. Constructor C1 produced
neighbour-completion pools in which every non-incumbent point is at exact unit
distance from >= 2 (deg2) or >= 3 (deg3) vertices of the 510 graph. Those are the
highest-constraint-density additions available, and therefore the most likely to
make an incumbent vertex redundant.

Incumbent vertices are tried for deletion FIRST (pass-2 finding), so the injected
constraints stay in play instead of being deleted straight back off.
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
from hn.minimizer import MUSReducer
from hn.point import Point

OUT = "/home/user/CustomLLM/catalog/search5.jsonl"


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
    return pts, F, d.get("meta", {})


def minimise(pool, idxs, rng, priority=None, passes=4, deadline=None):
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
        if deadline and time.time() > deadline:
            return cur
    return cur


def worker(a):
    pool_path, seed, total = a
    pts, F, meta = load_pool(pool_path)
    pool = UDGraph(pts, lineage={"op": "pool", "src": pool_path})
    key2i = {p.key(): i for i, p in enumerate(pool.points)}
    spts, _ = load_vtx("/home/user/CustomLLM/data/CNP-SAT/vtx/510.vtx", field=F)
    missing = [p for p in spts if p.key() not in key2i]
    if missing:
        return {"seed": seed, "status": f"pool missing {len(missing)} of 510"}
    B = sorted(key2i[p.key()] for p in spts)
    rng = random.Random(seed)
    t0 = time.time()
    name = os.path.basename(pool_path)
    best = list(B)
    log({"pool": name, "seed": seed, "n": len(best), "iter": -1,
         "pool_n": pool.n, "pool_m": pool.m})
    it = 0
    attempted = 0
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
        w = [cnt[v] ** 3 for v in cands]
        nadd = rng.randint(3, min(40, len(cands)))
        added = set()
        for _ in range(nadd * 5):
            if len(added) >= nadd:
                break
            added.add(rng.choices(cands, weights=w, k=1)[0])
        attempted += 1
        res = minimise(pool, sorted(bs | added), rng, priority=set(bs),
                       deadline=t0 + total)
        if res is None:
            continue
        # log EVERY attempt outcome so the sampling rate is auditable
        log({"pool": name, "seed": seed, "iter": it, "added": len(added),
             "result_n": len(res), "best_n": len(best),
             "elapsed": round(time.time() - t0, 1)})
        if len(res) < len(best):
            best = res
            improved += 1
            log({"pool": name, "seed": seed, "n": len(best), "iter": it,
                 "added": len(added), "IMPROVED": True,
                 "vertices": sorted(best), "pool_src": pool_path,
                 "elapsed": round(time.time() - t0, 1)})
    return {"pool": name, "seed": seed, "n": len(best), "iters": it,
            "attempted": attempted, "improved": improved,
            "wall": round(time.time() - t0, 1)}


if __name__ == "__main__":
    pools = os.environ.get(
        "HN_POOLS",
        "data/pools/P3_nc510_deg3.json,data/pools/P3_nc510_deg2.json"
    ).split(",")
    NW = int(os.environ.get("HN_WORKERS", "4"))
    T = float(os.environ.get("HN_TOTAL", "900"))
    base = int(os.environ.get("HN_SEEDBASE", "70000"))
    R = int(os.environ.get("HN_ROUNDS", "4"))
    for p in pools:
        pts, F, meta = load_pool(p)
        g = UDGraph(pts, lineage={"op": "pool"})
        print(f"{os.path.basename(p)}: n={g.n} m={g.m} meta={meta.get('name')}",
              flush=True)
    best = 10 ** 9
    with mp.Pool(NW) as P:
        for rd in range(R):
            args = [(pools[(rd * NW + i) % len(pools)], base + rd * NW + i, T)
                    for i in range(NW)]
            for rec in P.imap_unordered(worker, args):
                if rec.get("n") and rec["n"] < best:
                    best = rec["n"]
                print(f"rd{rd} {rec.get('pool')} seed={rec['seed']} "
                      f"n={rec.get('n')} attempted={rec.get('attempted')} "
                      f"improved={rec.get('improved')} wall={rec.get('wall')} "
                      f"BEST={best}", flush=True)
    print("DONE best=", best, flush=True)
