"""C3-orbit minimisation — the move vertex-criticality does not already forbid.

Why this is not just another basin hop
--------------------------------------
The 510 graph is vertex-critical: G-v is 4-colourable for EVERY single v. That
fact also kills naive orbit deletion from the 510 itself, since
G - {p, Rp, R2p} is a subgraph of G - p and therefore also 4-colourable. So
orbits are only interesting when the ambient set is strictly larger.

Constructor C1's measurement: R120 about the origin maps 482 of the 510 vertices
back into the set, and the C3 closure adds only 40 points (550 = 1 + 183*3). Also
510 = 3 * 170 exactly. So the natural object is the SYMMETRISED graph, where the
question becomes: can whole orbits be deleted from a symmetric 5-chromatic graph?
Criticality says nothing about that, because the 40 added points can compensate
for a removed 510-vertex.

Two modes:
  A  orbit-minimise the whole symmetric pool
  B  start from the 510, complete its partial orbits, then orbit-minimise with
     the incumbent's orbits tried first

Arithmetic: to beat the record we need <= 507. From 550 that is 15 orbit
deletions; from 510-plus-completion it is a net -3 or better.

Cost: an orbit pass costs |S|/3 solver calls instead of |S|, so it is ~3x cheaper
per pass than the vertex pass that has been running.

Soundness: the pool is detected ONCE by the certified float-free detector;
candidate subsets are obtained by restriction (an identity, not a measurement).
Any improvement is re-derived from exact coordinates and re-proved by
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
from hn.point import Point, Rotation

OUT = "/home/user/CustomLLM/catalog/orbit2.jsonl"


def log(rec):
    with open(OUT, "a") as fh:
        fh.write(json.dumps(rec) + "\n")
        fh.flush()


def load_pool(path):
    d = json.load(open(path))
    F = MultiQuadField(tuple(d["field"]))
    pts = [Point(F.elem([Fraction(a, b) for a, b in p["x"]]),
                 F.elem([Fraction(a, b) for a, b in p["y"]]))
           for p in d["points"]]
    return pts, F


def c3_orbits(pool, F):
    """Exact C3 orbit partition under R120 about the origin."""
    R = Rotation.by_degrees_60k(F, 2)
    key2i = {p.key(): i for i, p in enumerate(pool.points)}
    img = {}
    for i, p in enumerate(pool.points):
        j = key2i.get(R.apply(p).key())
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
        orbits.append(tuple(sorted(cyc)))
    return orbits


def orbit_pass(pool_adj, cur, orbits_of, rng, priority=None, deadline=None):
    """One orbit-deletion sweep. Deletion unit is a whole C3 orbit."""
    sub = restrict(pool_adj, cur)
    pos = {v: i for i, v in enumerate(sub.index)}
    R = MUSReducer(sub, 4)
    calls = 0
    try:
        if not R.is_unsat(list(range(sub.n))):
            return None, 0
        groups = {}
        for v in cur:
            groups.setdefault(orbits_of[v], []).append(v)
        gl = list(groups.values())
        if priority:
            hi = [g for g in gl if all(v in priority for v in g)]
            lo = [g for g in gl if not all(v in priority for v in g)]
            rng.shuffle(hi); rng.shuffle(lo)
            gl = hi + lo
        else:
            rng.shuffle(gl)
        live = set(cur)
        for g in gl:
            if deadline and time.time() > deadline:
                break
            if not all(v in live for v in g) or len(g) >= len(live):
                continue
            trial = live - set(g)
            if R.is_unsat([pos[v] for v in trial]):
                live = trial
        calls = R.calls
        return sorted(live), calls
    finally:
        R.close()


def orbit_minimise(pool_adj, start, orbits_of, rng, priority=None,
                   passes=6, deadline=None):
    cur = sorted(start)
    total = 0
    for _ in range(passes):
        new, c = orbit_pass(pool_adj, cur, orbits_of, rng, priority, deadline)
        total += c
        if new is None:
            return None, total
        if len(new) == len(cur):
            return new, total
        cur = new
        if deadline and time.time() > deadline:
            break
    return cur, total


def worker(a):
    pool_path, seed, total_s, mode = a
    pts, F = load_pool(pool_path)
    pool = UDGraph(pts, lineage={"op": "pool", "src": pool_path})
    padj = pool.adj
    orbits = c3_orbits(pool, F)
    orbits_of = {v: ob for ob in orbits for v in ob}
    sizes = {}
    for ob in orbits:
        sizes[str(len(ob))] = sizes.get(str(len(ob)), 0) + 1
    key2i = {p.key(): i for i, p in enumerate(pool.points)}
    spts, _ = load_vtx("/home/user/CustomLLM/data/CNP-SAT/vtx/510.vtx", field=F)
    have510 = all(p.key() in key2i for p in spts)
    B = sorted(key2i[p.key()] for p in spts) if have510 else []
    name = os.path.basename(pool_path)
    rng = random.Random(seed)
    t0 = time.time()
    deadline = t0 + total_s
    log({"pool": name, "seed": seed, "mode": mode, "pool_n": pool.n,
         "pool_m": pool.m, "orbits": len(orbits), "orbit_sizes": sizes,
         "has510": have510, "event": "start"})

    best = None
    calls = 0
    if mode == "A":
        # orbit-minimise the whole symmetric pool, repeatedly with fresh orders
        it = 0
        while time.time() < deadline:
            it += 1
            res, c = orbit_minimise(padj, list(range(pool.n)), orbits_of, rng,
                                    deadline=deadline)
            calls += c
            if res is None:
                break
            log({"pool": name, "seed": seed, "mode": "A", "iter": it,
                 "result_n": len(res), "orbits_left": len({orbits_of[v] for v in res}),
                 "elapsed": round(time.time() - t0, 1)})
            if best is None or len(res) < len(best):
                best = res
                if len(best) < 510:
                    log({"pool": name, "seed": seed, "mode": "A", "n": len(best),
                         "IMPROVED": True, "vertices": sorted(best),
                         "pool_src": pool_path,
                         "elapsed": round(time.time() - t0, 1)})
    else:
        if not have510:
            return {"seed": seed, "status": "pool lacks the 510"}
        # complete the 510's partial orbits, then orbit-minimise
        bs = set(B)
        completion = sorted({v for ob in {orbits_of[u] for u in B}
                             for v in ob if v not in bs})
        start = sorted(bs | set(completion))
        best = list(B)
        log({"pool": name, "seed": seed, "mode": "B", "event": "completion",
             "completion_pts": len(completion), "start_n": len(start)})
        it = 0
        while time.time() < deadline:
            it += 1
            res, c = orbit_minimise(padj, start, orbits_of, rng, priority=bs,
                                    deadline=deadline)
            calls += c
            if res is None:
                break
            log({"pool": name, "seed": seed, "mode": "B", "iter": it,
                 "start_n": len(start), "result_n": len(res),
                 "elapsed": round(time.time() - t0, 1)})
            if len(res) < len(best):
                best = res
                log({"pool": name, "seed": seed, "mode": "B", "n": len(best),
                     "IMPROVED": True, "vertices": sorted(best),
                     "pool_src": pool_path, "elapsed": round(time.time() - t0, 1)})
    return {"pool": name, "seed": seed, "mode": mode,
            "n": len(best) if best else None, "calls": calls,
            "orbits": len(orbits), "wall": round(time.time() - t0, 1)}


if __name__ == "__main__":
    jobs = []
    NW = int(os.environ.get("HN_WORKERS", "4"))
    T = float(os.environ.get("HN_TOTAL", "1500"))
    R = int(os.environ.get("HN_ROUNDS", "8"))
    base = int(os.environ.get("HN_SEEDBASE", "500000"))
    spec = os.environ.get("HN_ORBIT_JOBS", ",".join([
        "data/pools/P1b_510_C3.json:A",
        "data/pools/P3_ncD6_deg3.json:A",
        "data/pools/P1b_510_C3.json:B",
        "data/pools/P3_ncD6_deg3.json:B",
    ])).split(",")
    best = 10 ** 9
    with mp.Pool(NW) as P:
        for rd in range(R):
            args = []
            for i in range(NW):
                p, m = spec[(rd * NW + i) % len(spec)].split(":")
                args.append((p, base + rd * NW + i, T, m))
            for rec in P.imap_unordered(worker, args):
                if rec.get("n") and rec["n"] < best:
                    best = rec["n"]
                print(f"rd{rd} {rec.get('pool')} mode={rec.get('mode')} "
                      f"seed={rec['seed']} n={rec.get('n')} orbits={rec.get('orbits')} "
                      f"calls={rec.get('calls')} wall={rec.get('wall')} BEST={best}",
                      flush=True)
    print("DONE best=", best, flush=True)
