"""M0: exact arithmetic, unit-distance detector, and the full solve+verify path."""
import sys, os, json
sys.path.insert(0, "/home/user/CustomLLM/src")

from hn.field import MultiQuadField, DEGREY_FIELD, Rat
from hn.point import Point, Rotation, spindle_rotation
from hn.graph import UDGraph
from hn.detect import detect_edges, detect_edges_bruteforce_exact, audit_prune_margin, verify_edges_exact
from hn import constructions as C
from hn.cnf import encode_coloring, verify_clique
from hn.modelcheck import check_coloring_against_points
from hn.oracle import solve_and_verify

FAIL = []
def chk(name, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  [{extra}]" if extra else ""))
    if not cond: FAIL.append(name)

print("="*70); print("FIELD AXIOMS"); print("="*70)
f = DEGREY_FIELD
r3, r11, r33 = f.sqrt_gen(3), f.sqrt_gen(11), f.sqrt_gen(33)
chk("sqrt3^2 == 3", (r3*r3).equals_rational(3))
chk("sqrt11^2 == 11", (r11*r11).equals_rational(11))
chk("sqrt33^2 == 33", (r33*r33).equals_rational(33))
chk("sqrt3*sqrt11 == sqrt33", r3*r11 == r33)
chk("basis independence: sqrt3 != rational", not r3.is_rational())
chk("1/sqrt3 * sqrt3 == 1", (r3.inverse()*r3).equals_rational(1))
x = (f.rational(Rat(5,6)) + r11*Rat(1,6))
chk("inverse roundtrip", (x*x.inverse()).equals_rational(1))
chk("exact sign of sqrt3-1 > 0", (r3 - 1).sign() == 1)
chk("exact sign of sqrt3-2 < 0", (r3 - 2).sign() == -1)
chk("exact sign of sqrt33-sqrt3*sqrt11 == 0", (r33 - r3*r11).sign() == 0)
# a deliberately nasty near-zero: sqrt(33) - 5744562646/1000000000 > 0
nz = r33 - f.rational(Rat(5744562646, 10**9))
chk("tiny positive detected exactly", nz.sign() == 1, f"approx={nz.approx():.3e}")
nz2 = r33 - f.rational(Rat(5744562648, 10**9))
chk("tiny negative detected exactly", nz2.sign() == -1, f"approx={nz2.approx():.3e}")
try:
    Rotation.from_cos_sin(f, Rat(1,2), Rat(1,2)); chk("non-rotation rejected", False)
except ValueError: chk("non-rotation rejected", True)
chk("spindle rotation is an isometry", spindle_rotation(f) is not None)

print(); print("="*70); print("ADVERSARIAL NEAR-UNIT CASES"); print("="*70)
p,q = C.near_unit_rational_pair()
d2 = p.sqdist(q)
chk("near-unit rational NOT accepted", not p.is_unit_from(q),
    f"float d2-1={d2.approx()-1:.3e}")
chk("  ...and float would have accepted at 1e-9", abs(d2.approx()-1) < 1e-9)
p,q = C.near_unit_irrational_pair()
d2 = p.sqdist(q)
chk("near-unit irrational NOT accepted", not p.is_unit_from(q),
    f"float d2-1={d2.approx()-1:.3e}")
chk("  ...and float would have accepted at 1e-9", abs(d2.approx()-1) < 1e-9)
chk("  ...sqrt33 coefficient nonzero", d2.coeffs[3] != 0, f"c={d2.coeffs[3]}")
p,q = C.exact_unit_pair_hard()
chk("hard irrational unit pair ACCEPTED", p.is_unit_from(q))

print(); print("="*70); print("DETECTOR: fast vs exact brute force"); print("="*70)
for name, pts in [("moser", C.moser_spindle().points),
                  ("golomb", C.golomb_graph().points),
                  ("hexagon", C.unit_hexagon_points()),
                  ("minkowski hex+hex", C.minkowski_sum(C.unit_hexagon_points(), C.unit_hexagon_points()))]:
    fast = detect_edges(pts); slow = detect_edges_bruteforce_exact(pts)
    chk(f"detector agrees on {name}", fast == slow, f"n={len(pts)} m={len(fast)}")
    ok, bad = verify_edges_exact(pts, fast)
    chk(f"all {name} edges exactly unit", ok)

mar = audit_prune_margin(C.golomb_graph().points)
print(f"  prune audit (golomb): max float err on true edges = {mar['max_float_error_on_true_edges']:.3e}"
      f" (window {mar['prune_window']:.0e})")
chk("prune margin safe", mar['max_float_error_on_true_edges'] < mar['prune_window']/1000)
# adversarial set that stresses the filter
adv = list(C.golomb_graph().points) + [C.near_unit_rational_pair()[1], C.near_unit_irrational_pair()[1]]
fast = detect_edges(adv); slow = detect_edges_bruteforce_exact(adv)
chk("detector agrees on adversarial set", fast == slow, f"n={len(adv)} m={len(fast)}")

print(); print("="*70); print("KNOWN GRAPH INVARIANTS"); print("="*70)
ms = C.moser_spindle()
chk("Moser spindle n==7", ms.n == 7, f"n={ms.n}")
chk("Moser spindle m==11", ms.m == 11, f"m={ms.m}")
# Moser spindle: the shared apex has degree 4 (2 in each rhombus); the two far
# apexes and the four side vertices have degree 3. Sums to 22 = 2*11 edges.
chk("Moser spindle degrees", ms.degree_sequence() == [3,3,3,3,3,3,4], f"{ms.degree_sequence()}")
gol = C.golomb_graph()
chk("Golomb n==10", gol.n == 10, f"n={gol.n}")
chk("Golomb m==18", gol.m == 18, f"m={gol.m}")
hexg = C.unit_hexagon()
chk("hexagon n==7,m==12", hexg.n==7 and hexg.m==12, f"n={hexg.n} m={hexg.m}")

print(); print("="*70); print("SOLVE + PROOF-VERIFY PATH"); print("="*70)
AD = "/home/user/CustomLLM/artifacts/m0"
os.makedirs(AD, exist_ok=True)
def run(g, k, tag, expect):
    enc = encode_coloring(g.n, g.edges, k, adj=g.adj)
    if enc.fixed:
        chk(f"  {tag}: symmetry clique verified", verify_clique(list(enc.fixed), g.edges))
    cp = os.path.join(AD, f"{tag}.cnf"); enc.write(cp)
    r = solve_and_verify(cp, AD, tag, solver="kissat", timeout=600)
    print(f"  {tag}: verdict={r.verdict} checker={r.checker_verdict} "
          f"{r.wall_seconds:.2f}s vars={r.n_vars} cls={r.n_clauses} "
          f"proof={r.proof_bytes}B sha={(r.proof_sha256 or '')[:12]}")
    chk(f"{tag}: verdict == {expect}", r.verdict == expect, r.verdict)
    if expect == "UNSAT":
        chk(f"{tag}: drat-trim VERIFIED", r.checker_verdict == "VERIFIED", str(r.checker_verdict))
    if r.verdict == "SAT":
        mc = check_coloring_against_points(g.points, r.model, k)
        chk(f"{tag}: independent model check", mc["ok"], json.dumps(mc["problems"]))
        chk(f"{tag}: checker re-found same edge count", mc["edges_found_exactly"] == g.m,
            f"{mc['edges_found_exactly']} vs {g.m}")
    return r

run(ms, 3, "moser_k3", "UNSAT")
run(ms, 4, "moser_k4", "SAT")
run(gol, 3, "golomb_k3", "UNSAT")
run(gol, 4, "golomb_k4", "SAT")
run(hexg, 3, "hexagon_k3", "SAT")

print(); print("="*70)
print(f"M0 RESULT: {'ALL PASS' if not FAIL else 'FAILURES: ' + ', '.join(FAIL)}")
print("="*70)
sys.exit(1 if FAIL else 0)
