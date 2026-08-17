import sys, os, json, time, multiprocessing as mp
sys.path.insert(0,"/home/user/CustomLLM/src")
from hn.mathematica import load_vtx
from hn.field import MultiQuadField
from hn.graph import UDGraph
from hn.search import worker, blobify

NAMES=["510","517","529","553","610","633","803","826","874"]
F=MultiQuadField((3,5,11))
allk={}
for nm in NAMES:
    pts,_=load_vtx(f"data/CNP-SAT/vtx/{nm}.vtx", field=F)
    for p in pts: allk[p.key()]=p
pool=list(allk.values())
g=UDGraph(pool, lineage={"op":"union_published","srcs":NAMES})
print(f"pool n={g.n} m={g.m} hash={g.coord_hash()[:16]}", flush=True)
blob=blobify(g)
OUT="/home/user/CustomLLM/catalog/search_runs.jsonl"
os.makedirs(os.path.dirname(OUT),exist_ok=True)
BUDGET=float(os.environ.get("HN_BUDGET","600"))
NW=int(os.environ.get("HN_WORKERS","4"))
base=int(os.environ.get("HN_SEEDBASE","1000"))
rounds=int(os.environ.get("HN_ROUNDS","6"))
best=10**9
with mp.Pool(NW) as pool_:
    for rd in range(rounds):
        seeds=[base+rd*NW+i for i in range(NW)]
        args=[(blob,(3,5,11),4,s,BUDGET,OUT,None) for s in seeds]
        for rec in pool_.imap_unordered(worker,args):
            if rec.get("n") and rec["n"]<best: best=rec["n"]
            print(f"round{rd} seed={rec['seed']} n={rec.get('n')} core={rec.get('after_core')} "
                  f"batch={rec.get('after_batch')} calls={rec.get('calls')} wall={rec.get('wall')}s BEST={best}", flush=True)
print("SEARCH DONE best=",best, flush=True)
