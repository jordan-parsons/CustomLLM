"""Add-2 frontier search: the smallest move not yet ruled out.

State of the ladder to a record (<= 508 vertices):
  add 0, delete 2   IMPOSSIBLE - vertex-criticality of the 510
  add 1, delete 3   IMPOSSIBLE - corollary from the exhaustive substitution search
                    (any such graph forces a hit (w,v1), and every hit graph is
                    itself vertex-critical, so no second deletion exists)
  add 2, delete 4   OPEN  <-- this search

Exhaustive add-2 is out of reach: C(663,2) x 510 is about 112 million queries. So
this is randomised over PAIRS, but targeted precisely at the frontier - pairs are
drawn from the 663 candidates that survive the proved degree>=4 prune, weighted by
degree into the incumbent, and the incumbent's own vertices are tried for deletion
first so the injected constraints stay in play.

Starting points are the original 510 AND the 8 new graphs found by substitution,
since those are structurally different 510-vertex critical graphs and their add-2
neighbourhoods are not the same.
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

OUT = "/home/user/CustomLLM/catalog/add2.jsonl"
ADJ = B0 = CANDS = None

def log(r):
    with open(OUT, "a") as fh: fh.write(json.dumps(r) + "\n"); fh.flush()

def build():
    d = json.load(open("data/pools/P3_nc510_deg2.json"))
    F = MultiQuadField(tuple(d["field"]))
    pts = [Point(F.elem([Fraction(a,b) for a,b in p["x"]]),
                 F.elem([Fraction(a,b) for a,b in p["y"]])) for p in d["points"]]
    pool = UDGraph(pts, lineage={"op":"pool"})
    key2i = {p.key(): i for i,p in enumerate(pool.points)}
    spts,_ = load_vtx("data/CNP-SAT/vtx/510.vtx", field=F)
    B = sorted(key2i[p.key()] for p in spts)
    return [list(x) for x in pool.adj], B, pool.n

def init(adj, B, cands):
    global ADJ, B0, CANDS
    ADJ, B0, CANDS = adj, B, cands

def minimise(start, priority, rng, passes=4):
    cur = sorted(start)
    for _ in range(passes):
        sub = restrict(ADJ, cur); R = MUSReducer(sub, 4)
        try:
            if not R.is_unsat(list(range(sub.n))): return None
            keep = R.core_reduce(list(range(sub.n)))
            hi = [i for i in keep if sub.index[i] in priority]
            lo = [i for i in keep if sub.index[i] not in priority]
            rng.shuffle(hi); rng.shuffle(lo)
            keep = R.deletion_mus(keep, order=hi + lo)
            new = sorted(sub.index[i] for i in keep)
        finally:
            R.close()
        if len(new) == len(cur): return new
        cur = new
    return cur

def worker(a):
    label, base, seed, budget = a
    rng = random.Random(seed); t0 = time.time()
    bs = set(base); best = sorted(base)
    cand = [w for w in CANDS if w not in bs]
    it = 0; results = []
    while time.time() - t0 < budget:
        it += 1
        deg = {}
        for w in cand:
            c = sum(1 for u in ADJ[w] if u in set(best))
            if c >= 4: deg[w] = c
        if len(deg) < 2: break
        ws = list(deg); wt = [deg[w]**3 for w in ws]
        pair = set()
        for _ in range(20):
            if len(pair) >= 2: break
            pair.add(rng.choices(ws, weights=wt, k=1)[0])
        if len(pair) < 2: continue
        res = minimise(sorted(set(best) | pair), set(best), rng)
        if res is None: continue
        results.append(len(res))
        if len(res) < len(best):
            best = res
            log({"label": label, "seed": seed, "n": len(best), "iter": it,
                 "IMPROVED": True, "vertices": sorted(best),
                 "elapsed": round(time.time()-t0,1)})
    return {"label": label, "seed": seed, "n": len(best), "iters": it,
            "min_seen": min(results) if results else None,
            "wall": round(time.time()-t0,1)}

if __name__ == "__main__":
    adj, B, pooln = build()
    bs = set(B)
    cands = [v for v in range(pooln)
             if v not in bs and sum(1 for u in adj[v] if u in bs) >= 4]
    print(f"pool built; {len(cands)} candidates survive the proved deg>=4 prune", flush=True)
    hits = json.load(open("catalog/substitute_result.json"))["hits"]
    starts = [("orig510", B)]
    for i,h in enumerate(hits):
        starts.append((f"hit{i}", sorted((bs - {h['v']}) | {h['w']})))
    print(f"{len(starts)} starting graphs (original + 8 substitution graphs)", flush=True)
    NW = int(os.environ.get("HN_WORKERS","4"))
    T = float(os.environ.get("HN_TOTAL","1200"))
    R = int(os.environ.get("HN_ROUNDS","6"))
    base = int(os.environ.get("HN_SEEDBASE","1100000"))
    best = 10**9
    with mp.Pool(NW, initializer=init, initargs=(adj, B, cands)) as P:
        for rd in range(R):
            args = [(starts[(rd*NW+i) % len(starts)][0],
                     starts[(rd*NW+i) % len(starts)][1],
                     base+rd*NW+i, T) for i in range(NW)]
            for r in P.imap_unordered(worker, args):
                if r.get("n") and r["n"] < best: best = r["n"]
                print(f"rd{rd} {r['label']} seed={r['seed']} n={r['n']} "
                      f"iters={r['iters']} min_seen={r['min_seen']} "
                      f"wall={r['wall']}s BEST={best}", flush=True)
    print("DONE best=", best, flush=True)
