"""Strict DIMACS validator.

ADVERSARY-2 FINDING D1b/D1c. drat-trim has a parse-time path that prints
"c trivial UNSAT" and "s VERIFIED" *before* examining the proof at all, and
ordinary CNF malformations drive it there: a comment line between clauses, a
header clause count that is too high, a missing trailing 0, a duplicated `p`
line, or an over-long comment. On a SATISFIABLE formula with a 0-byte proof this
yields `s VERIFIED` with exit code 0 (reproduced).

Consequence: "an UNSAT is not a result until a checker says so" silently degrades
to "the solver said UNSAT". The defence is to refuse to hand the checker anything
we have not first proven well-formed, and to refuse to read a VERIFIED that came
from the trivial-UNSAT path.

This validator is deliberately stricter than the DIMACS spec: comments are only
allowed before the header, the header counts must match exactly, and every clause
must be 0-terminated. Our own encoder already emits exactly this shape, so
strictness costs nothing and closes the hole.
"""

from __future__ import annotations

from typing import List, Tuple


class CNFMalformed(Exception):
    pass


def validate_dimacs(path: str, allow_comments_after_header: bool = False) -> dict:
    """Strictly validate a DIMACS CNF. Raises CNFMalformed on any problem."""
    n_vars = None
    n_clauses = None
    seen_header = False
    clause_count = 0
    max_var = 0
    open_clause = False
    with open(path, "rb") as fh:
        for lineno, raw in enumerate(fh, 1):
            if len(raw) > 65536:
                raise CNFMalformed(
                    f"{path}:{lineno}: line longer than 64KiB ({len(raw)} bytes); "
                    "drat-trim's parser can misbehave on these"
                )
            try:
                line = raw.decode("ascii")
            except UnicodeDecodeError as e:
                raise CNFMalformed(f"{path}:{lineno}: non-ASCII byte: {e}") from e
            s = line.strip()
            if not s:
                continue
            if s[0] == "c":
                if seen_header and not allow_comments_after_header:
                    raise CNFMalformed(
                        f"{path}:{lineno}: comment after the header. This is the "
                        "exact shape that drives drat-trim into its trivial-UNSAT "
                        "path; refusing."
                    )
                continue
            if s[0] == "p":
                if seen_header:
                    raise CNFMalformed(f"{path}:{lineno}: duplicate 'p' header line")
                parts = s.split()
                if len(parts) != 4 or parts[1] != "cnf":
                    raise CNFMalformed(f"{path}:{lineno}: bad header {s!r}")
                try:
                    n_vars, n_clauses = int(parts[2]), int(parts[3])
                except ValueError as e:
                    raise CNFMalformed(f"{path}:{lineno}: bad header ints") from e
                if n_vars < 0 or n_clauses < 0:
                    raise CNFMalformed(f"{path}:{lineno}: negative header counts")
                seen_header = True
                continue
            if not seen_header:
                raise CNFMalformed(f"{path}:{lineno}: clause before header")
            toks = s.split()
            for t in toks:
                try:
                    v = int(t)
                except ValueError as e:
                    raise CNFMalformed(f"{path}:{lineno}: non-integer token {t!r}") from e
                if v == 0:
                    if not open_clause:
                        raise CNFMalformed(f"{path}:{lineno}: empty clause terminator")
                    clause_count += 1
                    open_clause = False
                else:
                    open_clause = True
                    a = abs(v)
                    if a > max_var:
                        max_var = a
    if not seen_header:
        raise CNFMalformed(f"{path}: no 'p cnf' header")
    if open_clause:
        raise CNFMalformed(f"{path}: final clause is not 0-terminated")
    if clause_count != n_clauses:
        raise CNFMalformed(
            f"{path}: header declares {n_clauses} clauses but {clause_count} found. "
            "A too-high count sends drat-trim to trivial UNSAT; refusing."
        )
    if max_var > n_vars:
        raise CNFMalformed(
            f"{path}: header declares {n_vars} vars but literal {max_var} appears"
        )
    return {
        "n_vars": n_vars,
        "n_clauses": n_clauses,
        "clauses_found": clause_count,
        "max_var": max_var,
        "ok": True,
    }
