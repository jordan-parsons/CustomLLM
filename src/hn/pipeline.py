"""End-to-end: graph -> encode -> solve -> verify -> verdict record."""
from __future__ import annotations
import json, os, time
from typing import Dict, Optional
from .cnf import encode_coloring, verify_clique
from .graph import UDGraph
from .modelcheck import check_coloring_against_points, check_coloring_against_edges
from .oracle import solve_and_verify

ART = os.environ.get("HN_ARTIFACTS", "/home/user/CustomLLM/artifacts")

def assess(g: UDGraph, k: int, tag: str, solver: str = "kissat",
           timeout: Optional[int] = 3600, seed: Optional[int] = None,
           break_symmetry: bool = True, artifact_dir: Optional[str] = None,
           deep_model_check: bool = True) -> Dict:
    ad = artifact_dir or os.path.join(ART, tag)
    os.makedirs(ad, exist_ok=True)
    enc = encode_coloring(g.n, g.edges, k, adj=g.adj, break_symmetry=break_symmetry)
    if enc.fixed and not verify_clique(list(enc.fixed), g.edges):
        raise AssertionError("SOUNDNESS ALARM: symmetry-breaking set is not a clique")
    cnf = os.path.join(ad, f"{tag}.k{k}.cnf"); enc.write(cnf)
    r = solve_and_verify(cnf, ad, f"{tag}.k{k}", solver=solver, timeout=timeout, seed=seed)
    rec = {
        "tag": tag, "k": k, "n": g.n, "m": g.m,
        "graph_hash": g.graph_hash(), "coord_hash": g.coord_hash(),
        "field": list(g.field.gens),
        "verdict": r.verdict, "solver": r.solver, "solver_version": r.solver_version,
        "seed": seed, "wall_seconds": round(r.wall_seconds, 3),
        "n_vars": r.n_vars, "n_clauses": r.n_clauses,
        "proof_path": r.proof_path, "proof_sha256": r.proof_sha256,
        "proof_bytes": r.proof_bytes, "checker": r.checker,
        "checker_verdict": r.checker_verdict,
        "checker_seconds": None if r.checker_seconds is None else round(r.checker_seconds,3),
        "encoding_justifications": enc.justifications,
        "symmetry_fixed": enc.fixed, "notes": r.notes, "cnf_path": cnf,
    }
    if r.verdict == "SAT":
        mc = (check_coloring_against_points(g.points, r.model, k) if deep_model_check
              else check_coloring_against_edges(g.n, g.edges, r.model, k))
        rec["model_check"] = mc
        if not mc["ok"]:
            rec["verdict"] = "SAT_MODELCHECK_FAILED"
    return rec
