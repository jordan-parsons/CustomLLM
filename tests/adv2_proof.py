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
def d1_forged_proofs_for_a_satisfiable_formula():
    """The actual soundness property: for a WELL-FORMED SATISFIABLE CNF, no
    proof whatsoever may make drat-trim say VERIFIED.

    (Damaging the proof of a genuinely UNSAT formula and still getting VERIFIED
    is NOT unsoundness -- drat-trim certifies the FORMULA, and if the remaining
    lemmas still yield a conflict the answer is correct. So the test has to be
    run against a satisfiable formula.)
    """
    # a satisfiable formula that is not trivially so
    sat_lines = ["p cnf 6 8",
                 "1 2 3 0", "-1 -2 0", "-2 -3 0", "4 5 0",
                 "-4 6 0", "-5 -6 0", "1 4 0", "-3 5 0"]
    satcnf = w(os.path.join(TMP, "sat6.cnf"), "\n".join(sat_lines) + "\n")
    r = run_solver(satcnf, solver="kissat", proof_path=os.path.join(TMP, "s.drat"))
    assert r.verdict == "SAT", f"fixture: expected SAT, got {r.verdict}"

    unsatcnf = w(os.path.join(TMP, "unsat.cnf"), UNSAT_CNF)
    good = os.path.join(TMP, "good.drat")
    run_solver(unsatcnf, solver="kissat", proof_path=good)
    with open(good) as fh:
        gtext = fh.read()

    forgeries = [
        ("empty proof", ""),
        ("whitespace only", "\n\n   \n"),
        ("bare empty clause, no derivation", "0\n"),
        ("comment claiming success", "c s VERIFIED\n"),
        ("comment claiming success then empty clause", "c s VERIFIED\n0\n"),
        ("garbage text", "not a proof\nhello\n"),
        ("delete every original clause then claim the empty clause",
         "".join(f"d {l}\n" for l in sat_lines[1:]) + "0\n"),
        ("assert a non-RUP unit then the empty clause", "-1 0\n-2 0\n-3 0\n0\n"),
        ("assert every literal false then the empty clause",
         "".join(f"-{i} 0\n" for i in range(1, 7)) + "0\n"),
        ("a valid proof of a DIFFERENT, unsatisfiable formula", gtext),
        ("p-line injection inside the proof", "p cnf 1 1\n1 0\n-1 0\n0\n"),
    ]
    rows = []
    for name, content in forgeries:
        p = w(os.path.join(TMP, "f%d.drat" % len(rows)), content)
        v, _, _ = check_proof(satcnf, p)
        rows.append((name, v))
    p = os.path.join(TMP, "rand.drat")
    with open(p, "wb") as fh:
        fh.write(os.urandom(512))
    rows.append(("random bytes", check_proof(satcnf, p)[0]))
    rows.append(("nonexistent proof path", check_proof(
        satcnf, os.path.join(TMP, "nope.drat"))[0]))
    rows.append(("nonexistent CNF path", check_proof(
        os.path.join(TMP, "nope.cnf"), good)[0]))

    wrong = [n for (n, v) in rows if v == "VERIFIED"]
    report("D1 forged proofs cannot verify a SATISFIABLE formula", not wrong,
           ("WRONGLY VERIFIED: " + ", ".join(wrong) + " || " if wrong else "") +
           "; ".join(f"{n} -> {v}" for n, v in rows))


def d1b_malformed_cnf_gives_a_vacuous_VERIFIED():
    """CRITICAL: several ordinary CNF malformations make drat-trim mis-parse the
    formula, print 'c trivial UNSAT' / 's VERIFIED', and NEVER LOOK AT THE PROOF.
    The formula below is SATISFIABLE and the proof file is EMPTY, and check_proof
    still returns VERIFIED."""
    rows = []
    cases = [
        ("well-formed satisfiable CNF (control)", "p cnf 2 2\n1 2 0\n-1 2 0\n"),
        ("one short comment line BETWEEN clauses",
         "p cnf 2 2\n1 2 0\nc a note\n-1 2 0\n"),
        ("comment line before the header (control)",
         "c a note\np cnf 2 2\n1 2 0\n-1 2 0\n"),
        ("header clause count too HIGH (3 declared, 2 present)",
         "p cnf 2 3\n1 2 0\n-1 2 0\n"),
        ("header clause count too LOW (control)",
         "p cnf 2 1\n1 2 0\n-1 2 0\n"),
        ("missing trailing 0 on the last clause",
         "p cnf 2 2\n1 2 0\n-1 2\n"),
        ("duplicated p line", "p cnf 2 2\np cnf 2 2\n1 2 0\n-1 2 0\n"),
        ("comment longer than drat-trim's 64KiB line buffer",
         "p cnf 2 2\n1 2 0\nc " + "x" * 70000 + "\n-1 2 0\n"),
    ]
    empty_proof = w(os.path.join(TMP, "empty.drat"), "")
    for name, text in cases:
        c = w(os.path.join(TMP, "m%d.cnf" % len(rows)), text)
        v, tail, _ = check_proof(c, empty_proof)
        rows.append((name, v))
    bad = [n for (n, v) in rows if v == "VERIFIED"]
    report("D1b malformed CNF -> VERIFIED without reading the proof", not bad,
           ("FALSE VERIFIED on a SATISFIABLE formula with an EMPTY proof: " +
            " | ".join(bad) + " || " if bad else "") +
           "; ".join(f"{n} -> {v}" for n, v in rows))


def d1c_end_to_end_false_verified_unsat():
    """The money shot: solve_and_verify() returning is_verified_unsat == True for
    a SATISFIABLE formula, with a ZERO-BYTE proof file.

    kissat is stubbed only to supply the exit code 20 that the real solver would
    supply for the formula the project actually intends to solve; everything
    else (drat-trim, check_proof, solve_and_verify) is the real code path. It
    shows that nothing downstream asserts that the proof was non-empty or that
    the checker actually consumed it."""
    cnf = w(os.path.join(TMP, "e2e.cnf"), "p cnf 2 2\n1 2 0\nc stray comment\n-1 2 0\n")
    real = oracle.KISSAT
    try:
        oracle.KISSAT = fake("fake_kissat_e2e",
                             'echo "s UNSATISFIABLE"; : > "$4"; exit 20\n')
        res = solve_and_verify(cnf, os.path.join(TMP, "e2e_art"), "e2e",
                               solver="kissat", compress_proof=False)
    finally:
        oracle.KISSAT = real
    hole = res.is_verified_unsat
    report("D1c end-to-end false verified UNSAT", not hole,
           f"solve_and_verify -> verdict={res.verdict}, "
           f"checker_verdict={res.checker_verdict}, "
           f"is_verified_unsat={res.is_verified_unsat}, "
           f"proof_bytes={res.proof_bytes} -- the formula is SATISFIABLE, the "
           "proof file is 0 bytes, and drat-trim never examined it")


def d1d_audit_project_cnfs():
    """Regression guard for D1b/D1c: every CNF the project has ever written must
    be well-formed, because a malformed one silently turns drat-trim into a
    rubber stamp. Checks header clause count, absence of comment lines, and
    clause terminators, over artifacts/**/*.cnf."""
    import glob
    bad = []
    files = sorted(glob.glob("/home/user/CustomLLM/artifacts/**/*.cnf",
                             recursive=True))
    for p in files:
        n = c = badterm = 0
        hdr = None
        for line in open(p):
            if line.startswith("p "):
                if hdr is not None:
                    bad.append(f"{p}: duplicate p line")
                hdr = line.split()
            elif line.startswith("c"):
                c += 1
            elif line.strip():
                n += 1
                if not line.rstrip().endswith("0"):
                    badterm += 1
        if hdr is None:
            bad.append(f"{p}: no header")
        elif int(hdr[3]) != n:
            bad.append(f"{p}: header says {hdr[3]} clauses, file has {n}")
        if c:
            bad.append(f"{p}: {c} comment line(s)")
        if badterm:
            bad.append(f"{p}: {badterm} clause(s) not terminated by 0")
    report("D1d every project CNF is well-formed (guard for D1b/D1c)", not bad,
           "; ".join(bad[:5]) or
           f"{len(files)} CNFs under artifacts/: header clause counts exact, "
           "zero comment lines, every clause terminated by 0 -- so no CURRENT "
           "result was produced through the D1b mis-parse path")


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
        d1_forged_proofs_for_a_satisfiable_formula()
        d1b_malformed_cnf_gives_a_vacuous_VERIFIED()
        d1c_end_to_end_false_verified_unsat()
        d1d_audit_project_cnfs()
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
