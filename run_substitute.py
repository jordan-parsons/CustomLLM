"""EXHAUSTIVE single-point substitution search.

Everything so far has been sampling. This is a bounded, exhaustive statement.

The question
-----------
The 510 is vertex-critical, so no SUBSET of it works: every 509-subset is
4-colourable, hence so is every smaller subset. Progress therefore requires
points outside the 510. The smallest such move is a substitution:

        (510 - v) + w        for v in the 510 and w outside it.

If any such graph is still 5-chromatic it is a genuinely different 510-vertex
graph, and a new starting point that criticality does not forbid - it may then
admit further deletion.

The prune, and why it is sound
------------------------------
Let H = 510 - v, which is 4-colourable by criticality. Adding a single vertex w
to a 4-colourable graph H yields a non-4-colourable graph IF AND ONLY IF every
proper 4-colouring of H assigns all four colours to N(w) n H. That plainly
requires

        |N(w) n H| >= 4.

Since N(w) n (510 - v) is contained in N(w) n 510, a necessary condition is

        deg_510(w) >= 4,        and >= 5 when v is itself a neighbour of w.

So candidates w with fewer than 4 neighbours in the 510 can be discarded with a
proof, not a heuristic. That is what turns an intractable sweep into a bounded
one, and it is why a negative result here is exhaustive rather than statistical.

The batching trick, which makes it fast as well as exhaustive
------------------------------------------------------------
Testing 663 candidates against each of 510 vertices is 338,130 queries. But
monotonicity collapses it. For a FIXED v, add ALL surviving candidates W at once:

    if (510 - v) + W  is 4-COLOURABLE
    then (510 - v) + w is 4-colourable for every w in W,

because (510 - v) + w is a subgraph of (510 - v) + W and 4-colourability is
inherited by subgraphs. So ONE satisfiable answer clears all 663 candidates for
that v. Only when the batch is UNSAT must we drill into individual w.

That turns 338,130 queries into 510 plus drill-downs, with an identical
exhaustive guarantee - the logic is a monotonicity argument, not a heuristic.

Encoding: one MUSReducer over 510 + all surviving candidates, with presence
literals; every query is a single assumption call.

Search-time answers steer only; any hit is re-proved by verify_candidate.py.
"""
import json, os, sys, time
import multiprocessing as mp
from fractions import Fraction
sys.path.insert(0, "/home/user/CustomLLM/src")
from hn.field import MultiQuadField
from hn.graph import UDGraph
from hn.mathematica import load_vtx
from hn.minimizer import MUSReducer, restrict
from hn.point import Point

OUT = "/home/user/CustomLLM/catalog/substitute.jsonl"
def log(r):
    with open(OUT, "a") as fh: fh.write(json.dumps(r) + "\n"); fh.flush()

def load_pool(path):
    d = json.load(open(path))
    F = MultiQuadField(tuple(d["field"]))
    pts = [Point(F.elem([Fraction(a,b) for a,b in p["x"]]),
                 F.elem([Fraction(a,b) for a,b in p["y"]])) for p in d["points"]]
    return pts, F

def setup(pool_path, min_deg=4):
    pts, F = load_pool(pool_path)
    pool = UDGraph(pts, lineage={"op":"pool"})
    key2i = {p.key(): i for i,p in enumerate(pool.points)}
    spts,_ = load_vtx("/home/user/CustomLLM/data/CNP-SAT/vtx/510.vtx", field=F)
    B = sorted(key2i[p.key()] for p in spts); bs = set(B)
    cands = []
    for v in range(pool.n):
        if v in bs: continue
        d = sum(1 for u in pool.adj[v] if u in bs)
        if d >= min_deg: cands.append((v, d))
    return pool, B, cands

def worker(a):
    pool_path, vchunk, min_deg = a
    pool, B, cands = setup(pool_path, min_deg)
    bs = set(B)
    W = [w for w, _ in cands]
    degw = dict(cands)
    keep = sorted(bs | set(W))
    sub = restrict(pool.adj, keep)
    pos = {v: i for i, v in enumerate(sub.index)}
    R = MUSReducer(sub, 4, break_symmetry=False)
    hits = []; batches = 0; drills = 0; cleared = 0; t0 = time.time()
    try:
        for v in vchunk:
            base = [pos[u] for u in bs if u != v]
            # BATCH: all candidates at once. SAT here clears every single w.
            batches += 1
            if not R.is_unsat(base + [pos[w] for w in W]):
                cleared += len(W)
                continue
            # batch UNSAT -> some individual w may work; drill in
            log({"event": "BATCH_UNSAT", "v": v,
                 "pool": os.path.basename(pool_path)})
            for w in W:
                nbrs = set(pool.adj[w]) & bs
                if degw[w] - (1 if v in nbrs else 0) < 4:
                    continue
                drills += 1
                if R.is_unsat(base + [pos[w]]):
                    hits.append({"w": w, "v": v, "deg_w": degw[w]})
                    log({"event": "HIT", "w": w, "v": v, "deg_w": degw[w],
                         "pool": os.path.basename(pool_path)})
    finally:
        R.close()
    return {"batches": batches, "drills": drills, "cleared": cleared,
            "hits": hits, "wall": round(time.time() - t0, 1), "calls": R.calls}

if __name__ == "__main__":
    pool_path = os.environ.get("HN_SUBPOOL", "data/pools/P3_nc510_deg2.json")
    min_deg = int(os.environ.get("HN_MINDEG", "4"))
    NW = int(os.environ.get("HN_WORKERS", "4"))
    pool, B, cands = setup(pool_path, min_deg)
    print(f"pool={os.path.basename(pool_path)} n={pool.n} m={pool.m}", flush=True)
    print(f"candidates with deg_510 >= {min_deg}: {len(cands)}", flush=True)
    print(f"worst-case (w,v) tests: {len(cands)*510:,} (prune cuts this further)", flush=True)
    print(f"batched plan: {len(B)} batch queries (one per v), "
          f"each clearing up to {len(cands)} candidates at once", flush=True)
    chunks = [B[i::NW] for i in range(NW)]
    args = [(pool_path, c, min_deg) for c in chunks if c]
    tb = td = tc = 0; all_hits = []
    with mp.Pool(len(args)) as P:
        for r in P.imap_unordered(worker, args):
            tb += r["batches"]; td += r["drills"]; tc += r["cleared"]
            all_hits += r["hits"]
            print(f"  chunk: batches={r['batches']} drills={r['drills']} "
                  f"cleared={r['cleared']:,} hits={len(r['hits'])} "
                  f"wall={r['wall']}s", flush=True)
    print(f"EXHAUSTIVE RESULT over pool {os.path.basename(pool_path)}:", flush=True)
    print(f"  {tb} batch queries + {td:,} drill-downs", flush=True)
    print(f"  (w,v) substitutions ruled out: {tc + td:,}", flush=True)
    print(f"  still 5-chromatic: {len(all_hits)}", flush=True)
    json.dump({"pool": pool_path, "min_deg": min_deg, "batches": tb,
               "drills": td, "cleared": tc, "hits": all_hits},
              open("catalog/substitute_result.json", "w"), indent=1)
