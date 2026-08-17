import sys
from pysat.solvers import Cadical153
from pysat.formula import IDPool
p=sys.argv[1]
E=[];n=0
for L in open(p):
    t=L.split()
    if not t: continue
    if t[0]=='p': n=int(t[2])
    elif t[0]=='e': E.append((int(t[1]),int(t[2])))
pool=IDPool(); v=lambda i,c: pool.id(('v',i,c))
with Cadical153() as s:
    for i in range(1,n+1): s.add_clause([v(i,c) for c in range(4)])
    for a,b in E:
        for c in range(4): s.add_clause([-v(a,c),-v(b,c)])
    if E:
        a,b=E[0]; s.add_clause([v(a,0)]); s.add_clause([v(b,1)])
    r=s.solve()
print(f"{p}: n={n} m={len(E)} 4-colorable={r} => chi {'<=4' if r else '>=5'}")
