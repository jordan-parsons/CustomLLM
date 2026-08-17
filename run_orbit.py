"""Orbit-deletion search: the one question vertex-criticality has NOT answered.

Vertex-criticality of the 510 graph says G-v is 4-colourable for every single v.
Note that this immediately kills naive orbit deletion from the 510 itself:
G - {p, Rp, R2p} is a subgraph of G - p, hence also 4-colourable. So orbits only
help in the ADD-then-DELETE setting.

Constructor C1's finding: the 510 is nearly C3-symmetric (R120 maps 482 of 510
vertices back onto the set), and 510 = 3 x 170 exactly. So the natural move is:

  * inject a C3-symmetric SET of ambient points (whole orbits, not singletons)
  * delete whole C3 orbits rather than single vertices

Two payoffs. First, it asks a question criticality has not answered, because a
symmetric perturbation followed by symmetric deletion never tests a lone vertex.
Second, an orbit pass costs |S|/3 solver calls instead of |S|, so it is ~3x
cheaper per pass, which directly attacks the sampling-rate constraint that
throttled passes 1 and 2.

To reach a record we need net -3 or better from 510, i.e. 507 or below, since 509
merely ties Parts and 508 would need a non-orbit deletion on top.

Search answers steer the search only; any improvement is certified by
verify_candidate.py with a DRAT proof and a checker verdict.
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
from hn.point import Point, Rotation

OUT = "/home/user/CustomLLM/catalog/orbit.jsonl"


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


def build_orbits(pool, F):
    """Partition pool indices into exact C3 orbits under R120 about the origin."""
    R = Rotation.by_degrees_60k(F, 2)  # 120 degrees
    key2i = {p.key(): i for i, p in enumerate(pool.points)}
    img = {}
    for i, p in enumerate(pool.points):
        q = R.apply(p)
        j = key2i.get(q.key())
        if j is not None:
            img[i] = j
    orbits, seen = [], set()
    for i in range(pool.n):
        if i in seen:
            continue
        cyc, cur = [], i
        while cur is not None and cur not in seen:
            seen.add(cur)
            cyc.append(cur)
            cur = img.get(cur)
            if cur == i:
                break
        orbits.append(tuple(sorted(cyc)))
    return orbits


def orbit_minimise(pool, idxs, orbits_of, rng, priority=None, passes=4, deadline=None):
    """Deletion MUS where the unit of deletion is a whole C3 orbit."""
    cur = sorted(idxs)
    for _ in range(passes):
        sub = UDGraph([pool.points[i] for i in cur], lineage={"op": "induced"})
        pos = {v: i for i, v in enumerate(cur)}
        R = MUSReducer(sub, 4)
        try:
            if not R.is_unsat(list(range(sub.n))):
                return None
            groups = {}
            for v in cur:
                groups.setdefault(orbits_of[v], []).append(v)
            gl = list(groups.values())
            if priority:
                hi = [g for g in gl if all(v in priority for v in g)]
                lo = [g for g in gl if not all(v in priority for v in g)]
                rng.shuffle(hi)
                rng.shuffle(lo)
                gl = hi + lo
            else:
                rng.shuffle(gl)
            live = set(cur)
            for g in gl:
                if deadline and time.time() > deadline:
                    break
                if not all(v in live for v in g):
                    continue
                if len(g) >= len(live):
                    continue
                trial = sorted(live - set(g))
                if R.is_unsat([pos[v] for v in trial]):
                    live = set(trial)
            new = sorted(live)
        finally:
            R.close()
        if len(new) == len(cur):
            return new
        cur = new
        if deadline and time.time() > deadline:
            return cur
    return cur


def worker(a):
    pool_path, seed, total = a
    pts, F = load_pool(pool_path)
    pool = UDGraph(pts, lineage={"op": "pool", "src": pool_path})
    orbits = build_orbits(pool, F)
    orbits_of = {}
    for ob in orbits:
        for v in ob:
            orbits_of[v] = ob
    key2i = {p.key(): i for i, p in enumerate(pool.points)}
    spts, _ = load_vtx("/home/user/CustomLLM/data/CNP-SAT/vtx/510.vtx", field=F)
    if any(p.key() not in key2i for p in spts):
        return {"seed": seed, "status": "pool missing 510 members"}
    B = sorted(key2i[p.key()] for p in spts)
    name = os.path.basename(pool_path)
    sizes = {}
    for ob in orbits:
        sizes[len(ob)] = sizes.get(len(ob), 0) + 1
    rng = random.Random(seed)
    t0 = time.time()
    best = list(B)
    log({"pool": name, "seed": seed, "iter": -1, "n": len(best),
         "pool_n": pool.n, "pool_m": pool.m, "orbit_size_hist": sizes})
    it = attempted = improved = 0
    while time.time() - t0 < total:
        it += 1
        bs = set(best)
        # candidate orbits entirely outside the incumbent, each member touching it
        cand = []
        for ob in orbits:
            if any(v in bs for v in ob):
                continue
            touch = min(sum(1 for u in pool.adj[v] if u in bs) for v in ob)
            if touch >= 2:
                cand.append((ob, touch))
        if not cand:
            break
        w = [t ** 3 for _, t in cand]
        nadd = rng.randint(2, min(12, len(cand)))
        chosen = set()
        for _ in range(nadd * 5):
            if len(chosen) >= nadd:
                break
            chosen.add(rng.choices([c[0] for c in cand], weights=w, k=1)[0])
        added = {v for ob in chosen for v in ob}
        attempted += 1
        res = orbit_minimise(pool, sorted(bs | added), orbits_of, rng,
                             priority=set(bs), deadline=t0 + total)
        if res is None:
            continue
        log({"pool": name, "seed": seed, "iter": it, "added": len(added),
             "orbits_added": len(chosen), "result_n": len(res),
             "best_n": len(best), "elapsed": round(time.time() - t0, 1)})
        if len(res) < len(best):
            best = res
            improved += 1
            log({"pool": name, "seed": seed, "n": len(best), "iter": it,
                 "IMPROVED": True, "vertices": sorted(best),
                 "pool_src": pool_path, "elapsed": round(time.time() - t0, 1)})
    return {"pool": name, "seed": seed, "n": len(best), "iters": it,
            "attempted": attempted, "improved": improved,
            "wall": round(time.time() - t0, 1)}


if __name__ == "__main__":
    pools = os.environ.get(
        "HN_POOLS", "data/pools/P3_ncD6_deg3.json,data/pools/P1b_510_C3.json"
    ).split(",")
    NW = int(os.environ.get("HN_WORKERS", "4"))
    T = float(os.environ.get("HN_TOTAL", "900"))
    base = int(os.environ.get("HN_SEEDBASE", "80000"))
    R = int(os.environ.get("HN_ROUNDS", "3"))
    best = 10 ** 9
    with mp.Pool(NW) as P:
        for rd in range(R):
            args = [(pools[(rd * NW + i) % len(pools)], base + rd * NW + i, T)
                    for i in range(NW)]
            for rec in P.imap_unordered(worker, args):
                if rec.get("n") and rec["n"] < best:
                    best = rec["n"]
                print(f"rd{rd} {rec.get('pool')} seed={rec['seed']} n={rec.get('n')} "
                      f"attempted={rec.get('attempted')} improved={rec.get('improved')} "
                      f"wall={rec.get('wall')} BEST={best}", flush=True)
    print("DONE best=", best, flush=True)
