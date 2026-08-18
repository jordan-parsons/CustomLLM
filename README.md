# Hadwiger–Nelson: chromatic number of the plane

An exact-arithmetic, proof-checked attack on the chromatic number of the plane.
Known bounds: 5 ≤ CNP ≤ 7.

**Result: the record was not beaten.** No 5-chromatic unit-distance graph below
509 vertices was found, and no 6-chromatic one. See
**[reports/FINAL_REPORT.md](reports/FINAL_REPORT.md)** for the full account,
including seven barren strategies and the measurements that killed each.

Best verified here: **510 vertices**, χ = 5, k=4 UNSAT with a drat-trim VERIFIED
proof — a reproduction of the known HeuleGraph510, one vertex worse than the
record (509, Parts 2020).

## Ground rules this repo actually enforces
- **No floating point decides anything.** Unit distances are confirmed exactly in
  a multiquadratic number field. The detector's prefilter is a *certified rational
  interval*, so it provably cannot miss a real edge; float appears only as drawing
  geometry in `dashboard/`.
- **An UNSAT is not a result until a checker says so.** Every claim carries a DRAT
  proof and a drat-trim verdict, with hashes recorded. The leaderboard query reads
  verified rows only, by construction.
- **Every SAT gets an independent model check** written without importing the
  encoder.

## Layout
| path | what |
|---|---|
| `src/hn/` | field arithmetic, exact points, certified detector, CNF, oracle, minimizer, catalog |
| `tests/` | M0 suite + the three adversaries' independent implementations |
| `reports/` | final report, pass reports, adversary reports, referee decisions |
| `data/pools/` | 32 exact ambient point pools |
| `artifacts/` | CNFs, DRAT/LRAT proofs, checker logs, verdict JSON |
| `dashboard/` | self-contained progress page (`build_dashboard.py`, `serve_dashboard.py`) |

## Quick start
```
python3 tests/test_m0.py      # exact arithmetic + detector + solve/verify, end to end
python3 build_dashboard.py    # regenerate the dashboard from live state
```
Solvers are built into `vendor/` (kissat, CaDiCaL, drat-trim).
