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

Encoding: one MUSReducer over 510 + all surviving candidates, with presence
literals; testing (510 - v + w) is then a single assumption query.

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
    pool_path, chunk, min_deg = a
    pool, B, cands = setup(pool_path, min_deg)
    bs = set(B)
    keep = sorted(bs | {w for w,_ in cands})
    sub = restrict(pool.adj, keep)
    pos = {v:i for i,v in enumerate(sub.index)}
    R = MUSReducer(sub, 4, break_symmetry=False)
    hits = []; tested = 0; t0 = time.time()
    try:
        for w, dw in chunk:
            nbrs = set(pool.adj[w]) & bs
            for v in B:
                # sound prune: need >=4 neighbours surviving in 510 - v
                eff = dw - (1 if v in nbrs else 0)
                if eff < 4: continue
                tested += 1
                S = [pos[u] for u in bs if u != v] + [pos[w]]
                if R.is_unsat(S):
                    hits.append({"w": w, "v": v, "deg_w": dw})
                    log({"event":"HIT","w":w,"v":v,"deg_w":dw,
                         "pool":os.path.basename(pool_path)})
    finally:
        R.close()
    return {"tested": tested, "hits": hits, "cands": len(chunk),
            "wall": round(time.time()-t0,1), "calls": R.calls}

if __name__ == "__main__":
    pool_path = os.environ.get("HN_SUBPOOL", "data/pools/P3_nc510_deg2.json")
    min_deg = int(os.environ.get("HN_MINDEG", "4"))
    NW = int(os.environ.get("HN_WORKERS", "4"))
    pool, B, cands = setup(pool_path, min_deg)
    print(f"pool={os.path.basename(pool_path)} n={pool.n} m={pool.m}", flush=True)
    print(f"candidates with deg_510 >= {min_deg}: {len(cands)}", flush=True)
    print(f"worst-case (w,v) tests: {len(cands)*510:,} (prune cuts this further)", flush=True)
    chunks = [cands[i::NW] for i in range(NW)]
    args = [(pool_path, c, min_deg) for c in chunks if c]
    tot_tested = 0; all_hits = []
    with mp.Pool(len(args)) as P:
        for r in P.imap_unordered(worker, args):
            tot_tested += r["tested"]; all_hits += r["hits"]
            print(f"  chunk done: cands={r['cands']} tested={r['tested']} "
                  f"hits={len(r['hits'])} wall={r['wall']}s", flush=True)
    print(f"EXHAUSTIVE RESULT: tested {tot_tested:,} (w,v) substitutions, "
          f"{len(all_hits)} still 5-chromatic", flush=True)
    json.dump({"pool": pool_path, "min_deg": min_deg, "tested": tot_tested,
               "hits": all_hits}, open("catalog/substitute_result.json","w"), indent=1)
