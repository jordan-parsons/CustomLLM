"""Test the substitution hits: are these new 510-vertex graphs reducible?

The exhaustive search found (w,v) pairs where (510 - v) + w is still 5-chromatic.
Each is a DIFFERENT 510-vertex graph from the original - not a subgraph of it - so
the original's vertex-criticality says nothing about them. If any one of them is
not itself vertex-critical, it reduces to 509 or below.
"""
import json, os, random, sys, time
import multiprocessing as mp
from fractions import Fraction
sys.path.insert(0, "/home/user/CustomLLM/src")
from hn.field import MultiQuadField
from hn.graph import UDGraph
from hn.mathematica import load_vtx
from hn.minimizer import MUSReducer, restrict
from hn.point import Point

OUT = "/home/user/CustomLLM/catalog/hits.jsonl"
def log(r):
    with open(OUT, "a") as fh: fh.write(json.dumps(r) + "\n"); fh.flush()

# The pool is built ONCE in the parent with the certified detector, and only its
# INTEGER adjacency is handed to workers. Previously each of 4 workers rebuilt the
# 4349-point pool independently and four concurrent copies of the exact-arithmetic
# geometry exhausted memory, killing the job after 4 of 24 runs. Workers never need
# the geometry: the edge set of an induced subgraph is determined by the pool's
# already-certified adjacency.
POOL_ADJ = None
POOL_B = None

def setup():
    d = json.load(open("data/pools/P3_nc510_deg2.json"))
    F = MultiQuadField(tuple(d["field"]))
    pts = [Point(F.elem([Fraction(a,b) for a,b in p["x"]]),
                 F.elem([Fraction(a,b) for a,b in p["y"]])) for p in d["points"]]
    pool = UDGraph(pts, lineage={"op":"pool"})
    key2i = {p.key(): i for i,p in enumerate(pool.points)}
    spts,_ = load_vtx("/home/user/CustomLLM/data/CNP-SAT/vtx/510.vtx", field=F)
    B = sorted(key2i[p.key()] for p in spts)
    return pool, B

def init_worker(adj, B):
    global POOL_ADJ, POOL_B
    POOL_ADJ, POOL_B = adj, B

def worker(a):
    idx, w, v, seed = a
    adj, B = POOL_ADJ, POOL_B
    S = sorted((set(B) - {v}) | {w})
    rng = random.Random(seed); t0 = time.time()
    assert len(S) == 510
    # 1. confirm still UNSAT
    sub = restrict(adj, S)
    R = MUSReducer(sub, 4)
    unsat = R.is_unsat(list(range(sub.n))); R.close()
    if not unsat:
        return {"hit": idx, "w": w, "v": v, "status": "NOT_UNSAT"}
    # 2. criticality scan + full MUS
    cur = list(S); calls = 0
    for p in range(6):
        sub = restrict(adj, cur)
        R = MUSReducer(sub, 4)
        try:
            keep = R.core_reduce(list(range(sub.n)))
            keep = R.deletion_mus(keep, rng=rng)
            new = sorted(sub.index[i] for i in keep); calls += R.calls
        finally:
            R.close()
        if len(new) == len(cur): break
        cur = new
    rec = {"hit": idx, "w": w, "v": v, "seed": seed, "start_n": len(S),
           "final_n": len(cur), "reduced_by": len(S)-len(cur),
           "calls": calls, "wall": round(time.time()-t0,1)}
    if len(cur) < 510:
        rec["BELOW_510"] = True; rec["vertices"] = cur
    log(rec)
    return rec

if __name__ == "__main__":
    hits = json.load(open("catalog/substitute_result.json"))["hits"]
    seeds = int(os.environ.get("HN_SEEDS","3"))
    jobs = [(i, h["w"], h["v"], 900000+j) for i,h in enumerate(hits) for j in range(seeds)]
    print(f"building pool once in parent...", flush=True)
    pool, B = setup()
    adj = [list(x) for x in pool.adj]
    print(f"pool n={pool.n} m={pool.m}; handing integer adjacency to workers", flush=True)
    del pool
    print(f"testing {len(hits)} hits x {seeds} seeds = {len(jobs)} runs", flush=True)
    best = 10**9
    with mp.Pool(4, initializer=init_worker, initargs=(adj, B)) as P:
        for r in P.imap_unordered(worker, jobs):
            fn = r.get("final_n")
            if fn and fn < best: best = fn
            print(f"hit{r['hit']} w={r['w']} v={r['v']} seed={r.get('seed')} "
                  f"-> {fn} (-{r.get('reduced_by')}) {r.get('status','')} BEST={best}", flush=True)
    print("DONE best=", best, flush=True)
