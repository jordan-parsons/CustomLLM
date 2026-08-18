"""Deletion-MUS to fixpoint on the published 5-chromatic graphs never tested.

Gap: 510, 517, 529 and 553 were confirmed to be deletion fixpoints. 610, 633,
803, 826 and 874 were NOT tested - they were assumed minimised because Heule
published them. But 826 and 874 ship with NO DRAT proof upstream, which hints at
less attention, and a graph that is not already a fixpoint could reduce to
something different from 510.

Each graph is minimised on its own vertex set (small encoding), several random
orders each. Cheap and directly on target.
"""
import json, os, random, sys, time
import multiprocessing as mp
sys.path.insert(0, "/home/user/CustomLLM/src")
from hn.field import MultiQuadField
from hn.graph import UDGraph
from hn.mathematica import load_vtx
from hn.minimizer import MUSReducer, restrict

OUT = "/home/user/CustomLLM/catalog/fixpoint.jsonl"
def log(r):
    with open(OUT, "a") as fh: fh.write(json.dumps(r) + "\n"); fh.flush()

def worker(a):
    name, seed = a
    F = MultiQuadField((3, 5, 11))
    pts, _ = load_vtx(f"/home/user/CustomLLM/data/CNP-SAT/vtx/{name}.vtx", field=F)
    g = UDGraph(pts, lineage={"op": "published", "src": name})
    rng = random.Random(seed); t0 = time.time()
    cur = list(range(g.n)); calls = 0
    for p in range(8):
        sub = restrict(g.adj, cur)
        R = MUSReducer(sub, 4)
        try:
            if not R.is_unsat(list(range(sub.n))):
                return {"graph": name, "seed": seed, "status": "colourable"}
            keep = R.core_reduce(list(range(sub.n)))
            keep = R.deletion_mus(keep, rng=rng)
            new = sorted(sub.index[i] for i in keep)
            calls += R.calls
        finally:
            R.close()
        if len(new) == len(cur): break
        cur = new
    rec = {"graph": name, "seed": seed, "start_n": g.n, "final_n": len(cur),
           "reduced_by": g.n - len(cur), "calls": calls,
           "wall": round(time.time() - t0, 1)}
    if len(cur) < 510:
        rec["BELOW_510"] = True; rec["vertices"] = cur
    log(rec)
    return rec

if __name__ == "__main__":
    names = os.environ.get("HN_FIX", "610,633,803,826,874").split(",")
    seeds = int(os.environ.get("HN_SEEDS", "3"))
    jobs = [(n, 800000 + i) for n in names for i in range(seeds)]
    best = 10**9
    with mp.Pool(int(os.environ.get("HN_WORKERS", "4"))) as P:
        for r in P.imap_unordered(worker, jobs):
            if r.get("final_n") and r["final_n"] < best: best = r["final_n"]
            print(f"{r.get('graph')} seed={r.get('seed')} {r.get('start_n')} -> "
                  f"{r.get('final_n')} (-{r.get('reduced_by')}) calls={r.get('calls')} "
                  f"wall={r.get('wall')}s BEST={best}", flush=True)
    print("DONE best=", best, flush=True)
