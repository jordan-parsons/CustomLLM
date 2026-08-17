#!/usr/bin/env python3
"""ADVERSARY 2 / CATEGORY D -- proof checking and verdict integrity.

Attacks:
  * hn.oracle.check_proof   -- can it be made to say VERIFIED wrongly?
  * hn.oracle.run_solver    -- exit-code mapping (0/10/20/other)
  * SolveResult.is_verified_unsat
  * hn.pipeline.assess      -- is a SAT whose model fails the check downgraded?
  * hn.catalog.leaderboard  -- can an unverified row reach it?

Part 1 uses the REAL kissat + drat-trim on real CNFs with deliberately damaged
proofs. Part 2 substitutes fake binaries (by patching oracle.KISSAT /
oracle.DRAT_TRIM, which run_solver/check_proof read at call time) to reach the
exit paths a real solver will not produce on demand.

Run:  python tests/adv2_proof.py
"""
import os
import shutil
import sqlite3
import stat
import sys
import tempfile

sys.path.insert(0, "/home/user/CustomLLM/src")

from hn import oracle  # noqa: E402
from hn.oracle import SolveResult, check_proof, run_solver, solve_and_verify  # noqa: E402

FAIL = []
TMP = tempfile.mkdtemp(prefix="adv2_proof_")


def report(name, ok, detail=""):
    print(f"[{'ok ' if ok else 'HOLE'}] {name} {detail}")
    if not ok:
        FAIL.append(name)


UNSAT_CNF = "p cnf 2 4\n1 2 0\n1 -2 0\n-1 2 0\n-1 -2 0\n"
SAT_CNF = "p cnf 2 2\n1 2 0\n-1 2 0\n"


def w(path, text):
    with open(path, "w") as fh:
        fh.write(text)
    return path


# ---------------------------------------------------------------------------
# D1  real drat-trim against damaged proofs
# ---------------------------------------------------------------------------
def d1_damaged_proofs():
    cnf = w(os.path.join(TMP, "unsat.cnf"), UNSAT_CNF)
    satcnf = w(os.path.join(TMP, "sat.cnf"), SAT_CNF)
    good = os.path.join(TMP, "good.drat")
    r = run_solver(cnf, solver="kissat", proof_path=good)
    if r.verdict != "UNSAT":
        report("D1 damaged proofs", False,
               f"setup failed: kissat said {r.verdict} on a trivially UNSAT CNF")
        return
    base_verdict, base_tail, _ = check_proof(cnf, good)
    rows = [("intact kissat proof", base_verdict)]

    def variant(name, content, binary=False):
        p = os.path.join(TMP, name.replace(" ", "_") + ".drat")
        mode = "wb" if binary else "w"
        with open(p, mode) as fh:
            fh.write(content)
        v, tail, _ = check_proof(cnf, p)
        rows.append((name, v))
        return v

    with open(good) as fh:
        gtext = fh.read()

    variant("empty proof", "")
    variant("whitespace-only proof", "\n\n   \n")
    variant("truncated proof (first half of lines)",
            "\n".join(gtext.splitlines()[: max(1, len(gtext.splitlines()) // 2)]) + "\n")
    variant("proof with the final empty clause removed",
            "\n".join(l for l in gtext.splitlines() if l.strip() != "0") + "\n")
    variant("garbage text", "this is not a proof at all\nhello world\n")
    variant("random bytes", os.urandom(512), binary=True)
    variant("bare empty clause with no derivation", "0\n")
    variant("comment claiming success", "c s VERIFIED\n")
    variant("comment claiming success then empty clause", "c s VERIFIED\n0\n")
    variant("unjustified lemma then empty clause", "1 0\n2 0\n0\n")
    # a proof of a DIFFERENT formula
    p2 = os.path.join(TMP, "other.drat")
    run_solver(satcnf, solver="kissat", proof_path=p2)
    v, _, _ = check_proof(cnf, p2)
    rows.append(("proof produced for a different (satisfiable) CNF", v))
    # missing proof file entirely
    v, _, _ = check_proof(cnf, os.path.join(TMP, "does_not_exist.drat"))
    rows.append(("nonexistent proof path", v))
    # missing CNF
    v, _, _ = check_proof(os.path.join(TMP, "nope.cnf"), good)
    rows.append(("nonexistent CNF path", v))

    wrongly_verified = [n for (n, v) in rows[1:] if v == "VERIFIED"]
    report("D1 real drat-trim vs damaged/forged proofs", not wrongly_verified,
           ("WRONGLY VERIFIED: " + ", ".join(wrongly_verified) + " | ") +
           "; ".join(f"{n} -> {v}" for n, v in rows))
    return rows


# ---------------------------------------------------------------------------
# D2  check_proof greps text and ignores the exit code
# ---------------------------------------------------------------------------
def fake(name, script):
    p = os.path.join(TMP, name)
    w(p, "#!/bin/sh\n" + script)
    os.chmod(p, os.stat(p).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return p


def d2_checker_interface():
    cnf = w(os.path.join(TMP, "d2.cnf"), UNSAT_CNF)
    proof = w(os.path.join(TMP, "d2.drat"), "0\n")
    real = oracle.DRAT_TRIM
    rows = []
    try:
        cases = [
            ("prints 's NOT VERIFIED', exit 1",
             "echo 's NOT VERIFIED'; exit 1", "NOT_VERIFIED"),
            ("prints 's TIMEOUT', exit 0",
             "echo 's TIMEOUT'; exit 0", "CHECKER_INCONCLUSIVE"),
            ("prints 's DERIVATION', exit 0",
             "echo 's DERIVATION'; exit 0", "CHECKER_INCONCLUSIVE"),
            ("prints nothing, exit 0", "exit 0", "CHECKER_INCONCLUSIVE"),
            ("segfault-ish: prints nothing, exit 139", "exit 139",
             "CHECKER_INCONCLUSIVE"),
            ("prints 's VERIFIED' but exits 1 (crash after the verdict)",
             "echo 's VERIFIED'; exit 1", "!VERIFIED-despite-failure"),
            ("prints 's VERIFIED' inside a COMMENT line and then NOT VERIFIED",
             "echo 'c note: s VERIFIED earlier'; echo 's NOT VERIFIED'; exit 1",
             "!VERIFIED-from-comment"),
            ("echoes an attacker-controlled path containing the magic string",
             "echo 'c error opening \"/artifacts/s VERIFIED/x.drat\".'; exit 1",
             "!VERIFIED-from-path-echo"),
            ("prints the string on stderr only",
             "echo 's VERIFIED' 1>&2; exit 1", "!VERIFIED-from-stderr"),
        ]
        holes = []
        for name, script, expect in cases:
            oracle.DRAT_TRIM = fake("fake_drat_" + str(len(rows)), script)
            v, tail, _ = check_proof(cnf, proof)
            rows.append((name, v))
            if expect.startswith("!") and v == "VERIFIED":
                holes.append(name)
    finally:
        oracle.DRAT_TRIM = real
    report("D2 check_proof accepts VERIFIED without integrity checks",
           not holes,
           "ACCEPTED AS VERIFIED: " + " | ".join(holes) + " || all cases: " +
           "; ".join(f"[{n}] -> {v}" for n, v in rows))


# ---------------------------------------------------------------------------
# D3  run_solver exit-code mapping and is_verified_unsat
# ---------------------------------------------------------------------------
def d3_exit_codes():
    cnf = w(os.path.join(TMP, "d3.cnf"), UNSAT_CNF)
    real = oracle.KISSAT
    rows = []
    problems = []
    try:
        cases = [
            ("exit 0 with no output", "exit 0", "TIMEOUT"),
            ("exit 20 (UNSAT) but writes NO proof file",
             "echo 's UNSATISFIABLE'; exit 20", "UNSAT"),
            ("exit 20 and writes an EMPTY proof file",
             'echo "s UNSATISFIABLE"; : > "$3"; exit 20', "UNSAT"),
            ("exit 10 (SAT) but prints no model",
             "echo 's SATISFIABLE'; exit 10", "SAT"),
            ("exit 10 and prints a model", "echo 's SATISFIABLE'; echo 'v 1 2 0'; exit 10",
             "SAT"),
            ("exit 1 (crash)", "echo 'boom' 1>&2; exit 1", "ERROR"),
            ("exit 42 (unknown)", "exit 42", "ERROR"),
            ("claims UNSATISFIABLE in stdout but exits 10",
             "echo 's UNSATISFIABLE'; exit 10", "SAT"),
        ]
        for name, script, expect in cases:
            oracle.KISSAT = fake("fake_kissat_" + str(len(rows)), script)
            # our fake receives args ... $3 is the proof path when 4 args are passed
            r = run_solver(cnf, solver="kissat", proof_path=os.path.join(TMP, "d3.drat"))
            rows.append((name, r.verdict, r.model))
            if r.verdict != expect:
                problems.append(f"{name}: verdict {r.verdict}, expected {expect}")
        # is_verified_unsat must require BOTH fields
        for verdict in ("UNSAT", "UNSAT_UNVERIFIED", "SAT", "TIMEOUT", "ERROR"):
            for cv in (None, "VERIFIED", "NOT_VERIFIED", "CHECKER_TIMEOUT",
                       "CHECKER_INCONCLUSIVE", "verified", "s VERIFIED"):
                res = SolveResult(verdict=verdict, solver="x", solver_version="x",
                                  wall_seconds=0, n_vars=0, n_clauses=0,
                                  checker_verdict=cv)
                want = (verdict == "UNSAT" and cv == "VERIFIED")
                if res.is_verified_unsat != want:
                    problems.append(f"is_verified_unsat({verdict},{cv})="
                                    f"{res.is_verified_unsat}")
    finally:
        oracle.KISSAT = real
    report("D3 run_solver exit-code mapping / is_verified_unsat", not problems,
           "; ".join(problems[:4]) or
           "; ".join(f"[{n}] -> {v}" for n, v, _ in rows) +
           " ; is_verified_unsat is True for exactly (UNSAT, 'VERIFIED') over "
           "35 combinations")


def d3b_solve_and_verify_no_proof():
    """A real UNSAT solved with want_proof=False must NOT be a verified UNSAT."""
    cnf = w(os.path.join(TMP, "d3b.cnf"), UNSAT_CNF)
    ad = os.path.join(TMP, "art_d3b")
    r = solve_and_verify(cnf, ad, "t", want_proof=False)
    ok1 = (r.verdict == "UNSAT_UNVERIFIED" and not r.is_verified_unsat)
    # and with a proof it must be verified
    r2 = solve_and_verify(cnf, os.path.join(TMP, "art_d3b2"), "t2")
    ok2 = r2.is_verified_unsat
    # now corrupt the archived proof AFTER checking: does anything notice?
    report("D3b solve_and_verify without a proof is never verified",
           ok1 and ok2,
           f"want_proof=False -> {r.verdict}/{r.checker_verdict} "
           f"(is_verified_unsat={r.is_verified_unsat}); with proof -> "
           f"{r2.verdict}/{r2.checker_verdict}")


# ---------------------------------------------------------------------------
# D4  SAT + failing model check must be downgraded
# ---------------------------------------------------------------------------
def d4_modelcheck_downgrade():
    from unittest import mock

    from hn.constructions import moser_spindle
    from hn.modelcheck import (check_coloring_against_edges,
                               check_coloring_against_points)
    from hn.pipeline import assess

    g = moser_spindle()
    problems = []

    # (a) an honest run: k=4 must be SAT with a passing model check
    rec = assess(g, 4, "adv2_spindle_k4", artifact_dir=os.path.join(TMP, "sp4"),
                 timeout=60)
    if rec["verdict"] != "SAT" or not rec["model_check"]["ok"]:
        problems.append(f"honest k=4 spindle: {rec['verdict']} "
                        f"{rec.get('model_check')}")

    # (b) a LYING solver: returns SAT with an all-one-colour model
    bogus = [1] + [-l for l in range(2, g.n * 4 + 1)]
    bogus = []
    for v in range(g.n):
        for c in range(4):
            bogus.append((v * 4 + c + 1) if c == 0 else -(v * 4 + c + 1))
    fake_res = SolveResult(verdict="SAT", solver="kissat", solver_version="fake",
                           wall_seconds=0.0, n_vars=g.n * 4, n_clauses=0,
                           model=bogus)
    with mock.patch("hn.pipeline.solve_and_verify", return_value=fake_res):
        rec2 = assess(g, 4, "adv2_spindle_lie",
                      artifact_dir=os.path.join(TMP, "splie"), timeout=60)
    if rec2["verdict"] != "SAT_MODELCHECK_FAILED":
        problems.append(f"monochromatic model was NOT downgraded: "
                        f"{rec2['verdict']}")

    # (c) an EMPTY model (solver printed no 'v' lines)
    fake_empty = SolveResult(verdict="SAT", solver="kissat", solver_version="fake",
                             wall_seconds=0.0, n_vars=g.n * 4, n_clauses=0,
                             model=[])
    with mock.patch("hn.pipeline.solve_and_verify", return_value=fake_empty):
        rec3 = assess(g, 4, "adv2_spindle_empty",
                      artifact_dir=os.path.join(TMP, "spempty"), timeout=60)
    if rec3["verdict"] != "SAT_MODELCHECK_FAILED":
        problems.append(f"empty model was NOT downgraded: {rec3['verdict']}")

    # (d) the shallow checker must also reject
    sh = check_coloring_against_edges(g.n, g.edges, bogus, 4)
    if sh["ok"]:
        problems.append("check_coloring_against_edges accepted a monochromatic "
                        "model")
    dp = check_coloring_against_points(g.points, bogus, 4)
    if dp["ok"]:
        problems.append("check_coloring_against_points accepted a monochromatic "
                        "model")
    report("D4 SAT with a failing model check is downgraded", not problems,
           "; ".join(problems[:4]) or
           f"honest k=4 Moser spindle -> SAT with model_check ok "
           f"({rec['model_check']['edges_found_exactly']} edges re-derived "
           "exactly); a monochromatic model and an empty model both produced "
           "verdict SAT_MODELCHECK_FAILED; both model checkers rejected them")


# ---------------------------------------------------------------------------
# D5  can an unverified row reach the leaderboard?
# ---------------------------------------------------------------------------
def d5_leaderboard():
    from hn.catalog import already_refuted, connect, leaderboard, record_attempt
    db = os.path.join(TMP, "cat.sqlite")
    con = connect(db)
    rows = [
        # (n, verdict, checker_verdict)  -- only the first should ever surface
        (100, "UNSAT", "VERIFIED"),
        (10, "UNSAT", None),
        (11, "UNSAT", "NOT_VERIFIED"),
        (12, "UNSAT", "CHECKER_TIMEOUT"),
        (13, "UNSAT", "CHECKER_INCONCLUSIVE"),
        (14, "UNSAT_UNVERIFIED", "VERIFIED"),
        (15, "UNSAT_UNVERIFIED", "NOT_VERIFIED"),
        (16, "SAT", "VERIFIED"),
        (17, "SAT_MODELCHECK_FAILED", "VERIFIED"),
        (18, "TIMEOUT", "VERIFIED"),
        (19, "ERROR", "VERIFIED"),
        (20, "UNSAT", "verified"),      # lower case must not match
        (21, "UNSAT", "s VERIFIED"),    # substring must not match
        (22, "UNSAT", " VERIFIED"),
    ]
    for n, verdict, cv in rows:
        record_attempt(con, {
            "coord_hash": f"c{n}", "graph_hash": f"g{n}", "n": n, "k": 4,
            "verdict": verdict, "checker_verdict": cv, "solver": "kissat",
        })
    lb = leaderboard(con, k=4, limit=50)
    surfaced = sorted(r["n_vertices"] for r in lb)
    problems = []
    if surfaced != [100]:
        problems.append(f"leaderboard surfaced {surfaced}, expected [100]")
    ar = [(n, already_refuted(con, f"g{n}", 4)) for n, _, _ in rows]
    wrong = [n for n, v in ar if v != (n == 100)]
    if wrong:
        problems.append(f"already_refuted wrong for graph_hash of n={wrong}")
    # a k mismatch must not leak either
    if leaderboard(con, k=5, limit=50):
        problems.append("k=5 leaderboard returned rows recorded at k=4")
    con.close()
    report("D5 leaderboard/already_refuted are verified-only", not problems,
           "; ".join(problems[:3]) or
           f"{len(rows)} rows inserted covering every verdict x checker_verdict "
           "combination incl. case and substring variants of 'VERIFIED': only "
           "the (UNSAT, VERIFIED) row surfaced, in the leaderboard and in "
           "already_refuted; k filtering is exact")


if __name__ == "__main__":
    try:
        d1_damaged_proofs()
        d2_checker_interface()
        d3_exit_codes()
        d3b_solve_and_verify_no_proof()
        d4_modelcheck_downgrade()
        d5_leaderboard()
    finally:
        print(f"\n(temp dir {TMP})")
    print()
    if FAIL:
        print("HOLES FOUND:", ", ".join(FAIL))
        sys.exit(1)
    print("no holes found in category D")
