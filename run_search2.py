"""Two-stage MUS descent: coarse pass on the big pool, then a FRESH small
encoding on the induced subgraph (far faster solving), with incremental logging
so the running best survives an unfinished run."""
import sys, os, json, time, random, multiprocessing as mp
sys.path.insert(0,"/home/user/CustomLLM/src")
from hn.mathematica import load_vtx
from hn.field import MultiQuadField
from hn.graph import UDGraph
from hn.minimizer import MUSReducer
from hn.search import batch_descent

OUT="/home/user/CustomLLM/catalog/search2.jsonl"

def log(rec):
    with open(OUT,"a") as fh: fh.write(json.dumps(rec)+"\n"); fh.flush()

def stage(g, k, S, rng, budget, tag, seed, deadline):
    """Run core_reduce + batch descent + deletion MUS on graph g restricted to S."""
    R=MUSReducer(g,k)
    try:
        if not R.is_unsat(S): return None
        S=R.core_reduce(S)
        t0=time.time()
        S=batch_descent(R,S,rng,time_budget=budget,t_start=t0)
        # single-vertex fixpoint with a hard deadline
        for p in range(6):
            before=len(S); order=list(S); rng.shuffle(order)
            for v in order:
                if time.time()>deadline: break
                if v not in S: continue
                trial=[u for u in S if u!=v]
                if R.is_unsat(trial): S=trial
            S=sorted(S)
            log({"tag":tag,"seed":seed,"stage":"pass","pass":p,"n":len(S),
                 "calls":R.calls,"elapsed":round(time.time()-t0,1)})
            if len(S)==before or time.time()>deadline: break
        return sorted(S)
    finally: R.close()

def worker(a):
    blob,gens,k,seed,budget,total = a
    from fractions import Fraction
    from hn.point import Point
    F=MultiQuadField(tuple(gens))
    pts=[Point(F.elem([Fraction(x,y) for x,y in xs]),F.elem([Fraction(x,y) for x,y in ys])) for xs,ys in blob]
    pool=UDGraph(pts,lineage={"op":"pool"})
    rng=random.Random(seed); t0=time.time(); deadline=t0+total
    # STAGE 1: coarse descent on the full pool
    S=stage(pool,k,list(range(pool.n)),rng,budget,"stage1",seed,min(deadline,t0+total*0.5))
    if S is None: return {"seed":seed,"status":"pool_colourable"}
    log({"tag":"stage1_done","seed":seed,"n":len(S),"elapsed":round(time.time()-t0,1)})
    # STAGE 2: rebuild a fresh, much smaller encoding on the induced subgraph
    sub=UDGraph([pool.points[i] for i in S],lineage={"op":"induced"})
    idxmap=S
    S2=stage(sub,k,list(range(sub.n)),rng,budget/3,"stage2",seed,deadline)
    if S2 is None: S2=list(range(sub.n))
    final=[idxmap[i] for i in S2]
    log({"tag":"FINAL","seed":seed,"n":len(final),"vertices":sorted(final),
         "wall":round(time.time()-t0,1)})
    return {"seed":seed,"status":"ok","n":len(final),"stage1":len(S),
            "wall":round(time.time()-t0,1)}

if __name__=="__main__":
    NAMES=["510","517","529","553","610","633","803","826","874"]
    F=MultiQuadField((3,5,11)); allk={}
    for nm in NAMES:
        pts,_=load_vtx(f"data/CNP-SAT/vtx/{nm}.vtx",field=F)
        for p in pts: allk[p.key()]=p
    g=UDGraph(list(allk.values()),lineage={"op":"union"})
    print(f"pool n={g.n} m={g.m}",flush=True)
    blob=[([[c.numerator,c.denominator] for c in p.x.coeffs],
           [[c.numerator,c.denominator] for c in p.y.coeffs]) for p in g.points]
    NW=int(os.environ.get("HN_WORKERS","4")); R=int(os.environ.get("HN_ROUNDS","10"))
    B=float(os.environ.get("HN_BUDGET","150")); T=float(os.environ.get("HN_TOTAL","500"))
    base=int(os.environ.get("HN_SEEDBASE","5000")); best=10**9
    with mp.Pool(NW) as P:
        for rd in range(R):
            args=[(blob,(3,5,11),4,base+rd*NW+i,B,T) for i in range(NW)]
            for rec in P.imap_unordered(worker,args):
                if rec.get("n") and rec["n"]<best: best=rec["n"]
                print(f"rd{rd} seed={rec['seed']} n={rec.get('n')} stage1={rec.get('stage1')} wall={rec.get('wall')} BEST={best}",flush=True)
    print("DONE best=",best,flush=True)
