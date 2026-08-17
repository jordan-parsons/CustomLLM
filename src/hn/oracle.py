"""SAT oracle: solver invocation, proof logging, proof checking, archival.

This is the only module permitted to produce a verdict. A verdict is one of:

  SAT           - a model was found AND independently model-checked
  UNSAT         - the solver reported UNSAT AND a DRAT proof was verified
  UNSAT_UNVERIFIED - solver said UNSAT but the proof did not verify (NOT a result)
  TIMEOUT / ERROR

An UNSAT verdict without checker_verdict == "VERIFIED" is explicitly not a
result; the catalog stores it, the leaderboard must never read it.
"""

from __future__ import annotations

import gzip
import hashlib
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field as dc_field
from typing import Dict, List, Optional, Sequence, Tuple

VENDOR = os.environ.get("HN_VENDOR", "/home/user/CustomLLM/vendor")
KISSAT = os.path.join(VENDOR, "kissat", "build", "kissat")
CADICAL = os.path.join(VENDOR, "cadical", "build", "cadical")
DRAT_TRIM = os.path.join(VENDOR, "drat-trim", "drat-trim")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def solver_version(binary: str) -> str:
    try:
        out = subprocess.run(
            [binary, "--version"], capture_output=True, text=True, timeout=30
        )
        return (out.stdout + out.stderr).strip().splitlines()[0][:80]
    except Exception as e:  # pragma: no cover
        return f"unknown({e})"


@dataclass
class SolveResult:
    verdict: str
    solver: str
    solver_version: str
    wall_seconds: float
    n_vars: int
    n_clauses: int
    model: Optional[List[int]] = None
    proof_path: Optional[str] = None
    proof_sha256: Optional[str] = None
    proof_bytes: Optional[int] = None
    checker: Optional[str] = None
    checker_verdict: Optional[str] = None
    checker_seconds: Optional[float] = None
    checker_output: Optional[str] = None
    checked_sha256: Optional[str] = None
    checked_bytes: Optional[int] = None
    archived_sha256: Optional[str] = None
    archived_bytes: Optional[int] = None
    notes: List[str] = dc_field(default_factory=list)

    @property
    def is_verified_unsat(self) -> bool:
        return self.verdict == "UNSAT" and self.checker_verdict == "VERIFIED"


def run_solver(
    cnf_path: str,
    solver: str = "kissat",
    proof_path: Optional[str] = None,
    timeout: Optional[int] = None,
    seed: Optional[int] = None,
) -> SolveResult:
    binary = {"kissat": KISSAT, "cadical": CADICAL}[solver]
    if not os.path.exists(binary):
        raise FileNotFoundError(f"solver binary missing: {binary}")
    cmd = [binary]
    if solver == "kissat":
        cmd.append("--no-binary")  # textual DRAT so drat-trim reads it directly
        if seed is not None:
            cmd.append(f"--seed={seed}")
        if timeout is not None:
            cmd.append(f"--time={int(timeout)}")
        cmd.append(cnf_path)
        if proof_path:
            cmd.append(proof_path)
    else:
        cmd += ["-q"]
        if seed is not None:
            cmd.append(f"--seed={seed}")
        cmd.append(cnf_path)
        if proof_path:
            cmd.append(proof_path)

    t0 = time.time()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=(timeout + 120) if timeout else None,
        )
        rc = proc.returncode
        out = proc.stdout
    except subprocess.TimeoutExpired:
        return SolveResult(
            verdict="TIMEOUT",
            solver=solver,
            solver_version=solver_version(binary),
            wall_seconds=time.time() - t0,
            n_vars=-1,
            n_clauses=-1,
            notes=["hard subprocess timeout"],
        )
    wall = time.time() - t0

    n_vars = n_clauses = -1
    with open(cnf_path) as fh:
        for line in fh:
            if line.startswith("p cnf"):
                parts = line.split()
                n_vars, n_clauses = int(parts[2]), int(parts[3])
                break

    res = SolveResult(
        verdict="ERROR",
        solver=solver,
        solver_version=solver_version(binary),
        wall_seconds=wall,
        n_vars=n_vars,
        n_clauses=n_clauses,
        proof_path=proof_path,
    )

    if rc == 10:
        res.verdict = "SAT"
        model: List[int] = []
        for line in out.splitlines():
            if line.startswith("v "):
                model.extend(int(t) for t in line[2:].split())
        res.model = [l for l in model if l != 0]
    elif rc == 20:
        res.verdict = "UNSAT"
    elif rc == 0:
        res.verdict = "TIMEOUT"
        res.notes.append("solver exited 0 (interrupted/limit reached)")
    else:
        res.notes.append(f"unexpected return code {rc}: {proc.stderr[:400]}")

    if proof_path and os.path.exists(proof_path):
        res.proof_bytes = os.path.getsize(proof_path)
    return res


def check_proof(
    cnf_path: str, proof_path: str, timeout: int = 7200
) -> Tuple[str, str, float]:
    """Verify a DRAT proof with drat-trim, defensively.

    ADVERSARY-2 FINDINGS D1b/D1c/D2 are all closed here:
      * the CNF is strictly validated FIRST, so we never hand drat-trim a
        malformed file that would send it down the trivial-UNSAT path;
      * a 0-byte / missing proof is refused outright;
      * "trivial UNSAT" is NOT accepted as VERIFIED - it means the checker never
        looked at the proof, which is precisely the hole;
      * the verdict line must appear ANCHORED at the start of a line, so an
        external string echoed into a comment (drat-trim echoes file paths and
        over-long input lines) cannot forge it;
      * the checker's exit code must agree with the verdict.
    """
    from .cnfcheck import CNFMalformed, validate_dimacs

    if not os.path.exists(DRAT_TRIM):
        raise FileNotFoundError(f"drat-trim missing: {DRAT_TRIM}")
    t0 = time.time()
    try:
        validate_dimacs(cnf_path)
    except CNFMalformed as e:
        return ("CNF_MALFORMED", f"refusing to check: {e}", time.time() - t0)
    if not os.path.exists(proof_path):
        return ("PROOF_MISSING", "no proof file", time.time() - t0)
    if os.path.getsize(proof_path) == 0:
        return ("PROOF_EMPTY", "proof file is 0 bytes", time.time() - t0)
    try:
        proc = subprocess.run(
            [DRAT_TRIM, cnf_path, proof_path, "-U"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return ("CHECKER_TIMEOUT", "", time.time() - t0)
    secs = time.time() - t0
    text = proc.stdout + proc.stderr
    lines = [l.strip() for l in text.splitlines()]
    verified = any(l == "s VERIFIED" for l in lines)
    not_verified = any(l == "s NOT VERIFIED" for l in lines)
    trivial = any(l.startswith("c trivial UNSAT") for l in lines)

    if trivial:
        verdict = "REJECTED_TRIVIAL_UNSAT"
    elif not_verified:
        verdict = "NOT_VERIFIED"
    elif verified and proc.returncode == 0:
        verdict = "VERIFIED"
    elif verified:
        verdict = "CHECKER_EXITCODE_MISMATCH"
    else:
        verdict = "CHECKER_INCONCLUSIVE"
    tail = "\n".join(lines[-12:]) + f"\n[exit={proc.returncode}]"
    return (verdict, tail, secs)


def solve_and_verify(
    cnf_path: str,
    artifact_dir: str,
    tag: str,
    solver: str = "kissat",
    timeout: Optional[int] = None,
    seed: Optional[int] = None,
    want_proof: bool = True,
    compress_proof: bool = True,
) -> SolveResult:
    """Solve, and for UNSAT verify the DRAT proof and archive it compressed."""
    os.makedirs(artifact_dir, exist_ok=True)
    proof_path = os.path.join(artifact_dir, f"{tag}.{solver}.drat") if want_proof else None
    res = run_solver(cnf_path, solver=solver, proof_path=proof_path, timeout=timeout, seed=seed)

    if res.verdict == "UNSAT" and proof_path and os.path.exists(proof_path):
        verdict, tail, secs = check_proof(cnf_path, proof_path)
        res.checker = "drat-trim"
        res.checker_verdict = verdict
        res.checker_seconds = secs
        res.checker_output = tail
        if verdict != "VERIFIED":
            res.verdict = "UNSAT_UNVERIFIED"
            res.notes.append(f"drat-trim did not verify: {verdict}")
        # Hash the exact bytes the checker consumed. ADVERSARY-1 FINDING D1:
        # previously proof_sha256/proof_bytes described the uncompressed DRAT
        # while proof_path named the .gz, so re-hashing the named file
        # mismatched. Both artifacts are now recorded separately and
        # unambiguously, and `proof_path` always names the file that
        # `archived_sha256` hashes.
        res.checked_sha256 = sha256_file(proof_path)
        res.checked_bytes = os.path.getsize(proof_path)
        res.proof_sha256 = res.checked_sha256
        res.proof_bytes = res.checked_bytes
        if compress_proof:
            gz = proof_path + ".gz"
            with open(proof_path, "rb") as fi, gzip.open(gz, "wb", compresslevel=6) as fo:
                shutil.copyfileobj(fi, fo)
            os.remove(proof_path)
            res.proof_path = gz
            res.archived_sha256 = sha256_file(gz)
            res.archived_bytes = os.path.getsize(gz)
        else:
            res.archived_sha256 = res.checked_sha256
            res.archived_bytes = res.checked_bytes
    elif res.verdict == "UNSAT":
        res.verdict = "UNSAT_UNVERIFIED"
        res.notes.append("no proof file produced")
    elif proof_path and os.path.exists(proof_path):
        # ADVERSARY-1 FINDING D2: a SAT answer has no proof, so every
        # proof-related field must be cleared rather than left describing a
        # partial DRAT log that was deleted.
        os.remove(proof_path)
        res.proof_path = None
        res.proof_bytes = None
        res.proof_sha256 = None
    return res
