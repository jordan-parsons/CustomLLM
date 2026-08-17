#!/usr/bin/env python3
"""ADVERSARY 1 / CHECK 1 -- a from-scratch, deliberately DIFFERENT SAT encoding
of k-colourability for the 510-vertex graph, plus an independent model checker.

This file shares NO code with src/hn/cnf.py.  Differences on purpose:

  1. COLOUR-MAJOR variable numbering:   var(v,c) = c*n + v + 1
     (src/hn/cnf.py uses vertex-major   var(v,c) = v*k + c + 1)
  2. AT-MOST-ONE-colour clauses ARE emitted (pairwise).  src/hn/cnf.py
     deliberately omits them.  With ALO + AMO each vertex gets EXACTLY one
     colour, so satisfying assignments are in bijection with proper
     k-colourings -- no "pick any true colour" post-processing step is needed,
     which removes that whole class of possible unsoundness.
  3. NO symmetry breaking of any kind.  No clique is pinned.  Nothing is
     assumed about the graph's structure.
  4. Edge set is (by default) RE-DERIVED FROM THE EXACT GEOMETRY by
     tests/adv1_exact.py, not read from data/CNP-SAT/edge/510.edge.
     So the chain is: Mathematica coordinates -> exact field arithmetic ->
     unit pairs -> CNF -> solver.  The .edge file is never trusted.
  5. Solved with cadical (the pipeline used kissat).

Soundness of this encoding, stated plainly:
  ALO(v):  var(v,0) v ... v var(v,k-1)
  AMO(v):  for c<d, -var(v,c) v -var(v,d)
  EDGE(u,v,c): -var(u,c) v -var(v,c)
  => an assignment satisfies all iff the map v -> the unique c with var(v,c)
     true is a proper k-colouring.  Both directions are immediate.
  Therefore UNSAT at k iff the graph is not k-colourable.

Usage:
  python3 tests/adv1_encode.py --k 4 --out DIR
  python3 tests/adv1_encode.py --k 5 --out DIR
  python3 tests/adv1_encode.py --verify-model MODEL.txt --k 5
"""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

CADICAL = os.path.join(ROOT, "vendor/cadical/build/cadical")
DRATTRIM = os.path.join(ROOT, "vendor/drat-trim/drat-trim")
VTX = os.path.join(ROOT, "data/CNP-SAT/vtx/510.vtx")
EDGE = os.path.join(ROOT, "data/CNP-SAT/edge/510.edge")


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


# ------------------------------------------------------------------ geometry
def unit_pairs_from_geometry(vtx_path: str):
    """Re-derive the unit-distance edge set exactly.  Returns (n, sorted pairs)
    with 1-based vertex indices matching the line order of the .vtx file."""
    import math

    import adv1_exact as A

    pts = A.parse_vtx(vtx_path)
    n = len(pts)
    D = 1
    for (x, y) in pts:
        for e in (x, y):
            for m in range(A.DIM):
                d = e.c[m].denominator
                D = D * d // math.gcd(D, d)
    ivx = [A.to_intvec(x, D) for (x, y) in pts]
    ivy = [A.to_intvec(y, D) for (x, y) in pts]
    D2 = D * D
    zt = [0] * (A.DIM - 1)
    out = []
    for i in range(n):
        for j in range(i + 1, n):
            acc = [0] * A.DIM
            for m, v in ivx[i]:
                acc[m] += v
            for m, v in ivx[j]:
                acc[m] -= v
            dx = [(m, acc[m]) for m in range(A.DIM) if acc[m]]
            acc = [0] * A.DIM
            for m, v in ivy[i]:
                acc[m] += v
            for m, v in ivy[j]:
                acc[m] -= v
            dy = [(m, acc[m]) for m in range(A.DIM) if acc[m]]
            s = A.sq_add(dx, dy)
            if s[0] == D2 and s[1:] == zt:
                out.append((i + 1, j + 1))
    return n, out


def read_edge_file(path: str):
    n = None
    out = []
    with open(path) as fh:
        for line in fh:
            t = line.split()
            if not t:
                continue
            if t[0] == "p":
                n = int(t[2])
            elif t[0] == "e":
                a, b = int(t[1]), int(t[2])
                out.append((min(a, b), max(a, b)))
    return n, sorted(out)


# ------------------------------------------------------------------ encoding
def var(v: int, c: int, n: int) -> int:
    """COLOUR-MAJOR numbering, 0-based v and c, 1-based literal."""
    return c * n + v + 1


def encode(n: int, edges, k: int):
    """Return (nvars, clauses).  ALO + pairwise AMO + edge clauses. No SBP."""
    clauses = []
    for v in range(n):
        clauses.append([var(v, c, n) for c in range(k)])          # ALO
    for v in range(n):
        for c in range(k):
            for d in range(c + 1, k):
                clauses.append([-var(v, c, n), -var(v, d, n)])    # AMO
    for (a, b) in edges:
        u, w = a - 1, b - 1
        for c in range(k):
            clauses.append([-var(u, c, n), -var(w, c, n)])        # edge
    return n * k, clauses


def write_dimacs(path: str, nvars: int, clauses):
    with open(path, "w") as fh:
        fh.write(f"p cnf {nvars} {len(clauses)}\n")
        fh.write("".join(" ".join(map(str, cl)) + " 0\n" for cl in clauses))


# ------------------------------------------------------------- model checking
def parse_model(text: str):
    """Collect literals from cadical 'v ' lines."""
    lits = []
    for line in text.splitlines():
        if line.startswith("v "):
            for tok in line[2:].split():
                x = int(tok)
                if x == 0:
                    continue
                lits.append(x)
    return lits


def check_model(lits, n: int, k: int, edges):
    """Independent verification of a k-colouring, written from scratch.
    Returns (ok, messages, colouring)."""
    true_set = {x for x in lits if x > 0}
    msgs = []
    colour = [None] * n
    multi = []
    for v in range(n):
        cs = [c for c in range(k) if var(v, c, n) in true_set]
        if len(cs) == 0:
            msgs.append(f"vertex {v+1} has NO colour")
        elif len(cs) > 1:
            multi.append((v + 1, cs))
            colour[v] = cs[0]
        else:
            colour[v] = cs[0]
    if multi:
        msgs.append(f"{len(multi)} vertices carry >1 true colour var (AMO violated!): {multi[:5]}")
    bad = []
    for (a, b) in edges:
        if colour[a - 1] is None or colour[b - 1] is None:
            continue
        if colour[a - 1] == colour[b - 1]:
            bad.append((a, b, colour[a - 1]))
    if bad:
        msgs.append(f"{len(bad)} MONOCHROMATIC edges: {bad[:10]}")
    used = sorted({c for c in colour if c is not None})
    msgs.append(f"colours actually used: {used} ({len(used)} of {k})")
    ok = not bad and all(c is not None for c in colour) and not multi
    return ok, msgs, colour


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, required=True)
    ap.add_argument("--out", default=os.path.join(ROOT, "artifacts/adv1"))
    ap.add_argument("--edge-source", choices=["geometry", "file"], default="geometry")
    ap.add_argument("--no-proof", action="store_true")
    ap.add_argument("--timeout", type=int, default=100000)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    k = args.k
    print("=" * 74)
    print(f"ADVERSARY 1 / CHECK 1 -- independent encoding, k={k}, solver=cadical")
    print("=" * 74)

    t0 = time.time()
    if args.edge_source == "geometry":
        n, edges = unit_pairs_from_geometry(VTX)
        print(f"[geom] re-derived edge set EXACTLY from {VTX}")
        print(f"[geom] n={n} exact unit pairs={len(edges)}  ({time.time()-t0:.1f}s)")
        nf, ef = read_edge_file(EDGE)
        same = (nf == n and ef == sorted(edges))
        print(f"[geom] identical to data/CNP-SAT/edge/510.edge ? {same}")
        if not same:
            print("*** ALARM: geometry-derived edge set differs from the .edge file")
            print(f"    only-in-geometry: {sorted(set(edges)-set(ef))[:10]}")
            print(f"    only-in-file    : {sorted(set(ef)-set(edges))[:10]}")
    else:
        n, edges = read_edge_file(EDGE)
        print(f"[file] edges read from {EDGE}: n={n} m={len(edges)}")

    nvars, clauses = encode(n, edges, k)
    # expected clause counts, checked explicitly
    exp = n + n * (k * (k - 1) // 2) + len(edges) * k
    print(f"\n[encode] colour-major var(v,c)=c*n+v+1 ; ALO+AMO+edges ; NO symmetry breaking")
    print(f"[encode] vars={nvars} clauses={len(clauses)} (expected {exp}) "
          f"= {n} ALO + {n*(k*(k-1)//2)} AMO + {len(edges)*k} edge")
    assert len(clauses) == exp, "clause count mismatch"
    # cross-check: distinct from the pipeline's numbering
    print(f"[encode] sanity: var(0,1)={var(0,1,n)} (vertex-major would give 2)")

    cnf = os.path.join(args.out, f"adv1_510_k{k}.cnf")
    write_dimacs(cnf, nvars, clauses)
    print(f"[encode] wrote {cnf}\n         bytes={os.path.getsize(cnf)} sha256={sha256(cnf)}")

    proof = os.path.join(args.out, f"adv1_510_k{k}.cadical.drat")
    cmd = [CADICAL, "--no-binary", "-q", cnf]
    if not args.no_proof:
        cmd.append(proof)
    print(f"\n[solve] $ {' '.join(cmd)}")
    ts = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=args.timeout)
    solve_s = time.time() - ts
    verdict = None
    for line in r.stdout.splitlines():
        if line.startswith("s "):
            verdict = line[2:].strip()
    print(f"[solve] cadical exit={r.returncode} verdict={verdict} time={solve_s:.1f}s")
    if r.stderr.strip():
        print(f"[solve] stderr: {r.stderr.strip()[:500]}")

    if verdict == "SATISFIABLE":
        if k == 4:
            print("\n" + "!" * 74)
            print("*** SOUNDNESS ALARM: k=4 SATISFIABLE. The claim chi>=5 is REFUTED")
            print("!" * 74)
        lits = parse_model(r.stdout)
        mpath = os.path.join(args.out, f"adv1_510_k{k}.model")
        with open(mpath, "w") as fh:
            fh.write("\n".join(map(str, lits)) + "\n")
        ok, msgs, colour = check_model(lits, n, k, edges)
        print(f"\n[modelcheck] independent checker on {len(lits)} literals -> "
              f"{'VALID PROPER COLOURING' if ok else 'INVALID'}")
        for m in msgs:
            print(f"[modelcheck]   {m}")
        cpath = os.path.join(args.out, f"adv1_510_k{k}.colouring")
        with open(cpath, "w") as fh:
            for v in range(n):
                fh.write(f"{v+1} {colour[v]}\n")
        print(f"[modelcheck] model    {mpath} bytes={os.path.getsize(mpath)} sha256={sha256(mpath)}")
        print(f"[modelcheck] colouring {cpath} bytes={os.path.getsize(cpath)} sha256={sha256(cpath)}")
        return 0 if ok else 1

    if verdict != "UNSATISFIABLE":
        print(f"*** INCONCLUSIVE: cadical returned {verdict!r}")
        return 1

    print(f"\n[proof] {proof}")
    print(f"[proof] bytes={os.path.getsize(proof)} sha256={sha256(proof)}")
    dcmd = [DRATTRIM, cnf, proof, "-f"]
    print(f"[verify] $ {' '.join(dcmd)}")
    tv = time.time()
    dr = subprocess.run(dcmd, capture_output=True, text=True, timeout=args.timeout)
    print(f"[verify] drat-trim exit={dr.returncode} time={time.time()-tv:.1f}s")
    tail = [l for l in dr.stdout.splitlines() if l.startswith("s ") or "VERIFIED" in l
            or "NOT" in l or "TRIVIAL" in l]
    for l in tail:
        print(f"[verify] {l}")
    verified = any("s VERIFIED" in l for l in dr.stdout.splitlines())
    print(f"\n[verify] CHECKER VERDICT: {'VERIFIED' if verified else 'NOT VERIFIED'}")
    log = os.path.join(args.out, f"adv1_510_k{k}.drattrim.log")
    with open(log, "w") as fh:
        fh.write(dr.stdout + "\n--stderr--\n" + dr.stderr)
    print(f"[verify] log {log} sha256={sha256(log)}")
    return 0 if verified else 1


if __name__ == "__main__":
    sys.exit(main())
