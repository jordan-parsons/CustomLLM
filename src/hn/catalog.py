"""SQLite catalog: every attempt, forever, with artifacts.

Schema follows spec section 9. The leaderboard query reads ONLY rows whose
verdict is UNSAT *and* whose checker_verdict is VERIFIED, so an unverified
solver answer can never reach it.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from typing import Dict, List, Optional

DB_PATH = os.environ.get("HN_CATALOG", "/home/user/CustomLLM/catalog/hn.sqlite")

SCHEMA = """
CREATE TABLE IF NOT EXISTS graphs (
  coord_hash TEXT PRIMARY KEY,
  graph_hash TEXT NOT NULL,
  n_vertices INTEGER NOT NULL,
  n_edges    INTEGER NOT NULL,
  field_id   TEXT NOT NULL,
  coord_blob TEXT NOT NULL,
  lineage    TEXT,
  created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS attempts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  coord_hash TEXT NOT NULL,
  graph_hash TEXT NOT NULL,
  n_vertices INTEGER NOT NULL,
  k INTEGER NOT NULL,
  verdict TEXT NOT NULL,
  solver TEXT, solver_version TEXT, seed INTEGER,
  wall_seconds REAL, n_vars INTEGER, n_clauses INTEGER,
  proof_path TEXT, proof_sha256 TEXT, proof_bytes INTEGER,
  checker TEXT, checker_verdict TEXT, checker_seconds REAL,
  checked_sha256 TEXT, checked_bytes INTEGER,
  archived_sha256 TEXT, archived_bytes INTEGER,
  encoding_justifications TEXT, symmetry_fixed TEXT,
  model_check TEXT, notes TEXT, created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS lineage (
  child_hash TEXT NOT NULL, parent_hash TEXT,
  operation TEXT, params TEXT, created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_attempts_lb ON attempts(k, verdict, checker_verdict, n_vertices);
CREATE INDEX IF NOT EXISTS idx_graphs_n ON graphs(n_vertices);
CREATE INDEX IF NOT EXISTS idx_graphs_gh ON graphs(graph_hash);
"""


def connect(path: str = DB_PATH) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    con = sqlite3.connect(path, timeout=60)
    con.executescript(SCHEMA)
    con.commit()
    return con


def register_graph(con: sqlite3.Connection, g, lineage: Optional[Dict] = None) -> str:
    ch = g.coord_hash()
    cur = con.execute("SELECT coord_hash FROM graphs WHERE coord_hash=?", (ch,))
    if cur.fetchone():
        return ch
    con.execute(
        "INSERT INTO graphs (coord_hash,graph_hash,n_vertices,n_edges,field_id,"
        "coord_blob,lineage,created_at) VALUES (?,?,?,?,?,?,?,?)",
        (
            ch,
            g.graph_hash(),
            g.n,
            g.m,
            json.dumps(list(g.field.gens)),
            json.dumps(g.to_dict()["points"]),
            json.dumps(lineage or g.lineage),
            time.time(),
        ),
    )
    if lineage or g.lineage:
        lg = lineage or g.lineage
        con.execute(
            "INSERT INTO lineage (child_hash,parent_hash,operation,params,created_at)"
            " VALUES (?,?,?,?,?)",
            (ch, lg.get("parent"), lg.get("op"), json.dumps(lg), time.time()),
        )
    con.commit()
    return ch


def record_attempt(con: sqlite3.Connection, rec: Dict) -> int:
    cur = con.execute(
        "INSERT INTO attempts (coord_hash,graph_hash,n_vertices,k,verdict,solver,"
        "solver_version,seed,wall_seconds,n_vars,n_clauses,proof_path,proof_sha256,"
        "proof_bytes,checker,checker_verdict,checker_seconds,"
        "checked_sha256,checked_bytes,archived_sha256,archived_bytes,"
        "encoding_justifications,symmetry_fixed,model_check,notes,created_at)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            rec["coord_hash"], rec["graph_hash"], rec["n"], rec["k"], rec["verdict"],
            rec.get("solver"), rec.get("solver_version"), rec.get("seed"),
            rec.get("wall_seconds"), rec.get("n_vars"), rec.get("n_clauses"),
            rec.get("proof_path"), rec.get("proof_sha256"), rec.get("proof_bytes"),
            rec.get("checker"), rec.get("checker_verdict"), rec.get("checker_seconds"),
            rec.get("checked_sha256"), rec.get("checked_bytes"),
            rec.get("archived_sha256"), rec.get("archived_bytes"),
            json.dumps(rec.get("encoding_justifications")),
            json.dumps(rec.get("symmetry_fixed")),
            json.dumps(rec.get("model_check")),
            json.dumps(rec.get("notes")), time.time(),
        ),
    )
    con.commit()
    return cur.lastrowid


def already_refuted(con: sqlite3.Connection, graph_hash: str, k: int) -> bool:
    """Have we already got a VERIFIED non-k-colourability for this abstract graph?"""
    cur = con.execute(
        "SELECT 1 FROM attempts WHERE graph_hash=? AND k=? AND verdict='UNSAT'"
        " AND checker_verdict='VERIFIED' LIMIT 1",
        (graph_hash, k),
    )
    return cur.fetchone() is not None


def seen_graph_hash(con: sqlite3.Connection, graph_hash: str) -> List[str]:
    cur = con.execute("SELECT coord_hash FROM graphs WHERE graph_hash=?", (graph_hash,))
    return [r[0] for r in cur.fetchall()]


def leaderboard(con: sqlite3.Connection, k: int = 4, limit: int = 20) -> List[Dict]:
    """Smallest VERIFIED non-k-colourable graphs. Verified-only, by construction."""
    cur = con.execute(
        "SELECT n_vertices,coord_hash,graph_hash,proof_sha256,proof_bytes,solver,"
        "checker,checker_verdict,wall_seconds,archived_sha256,archived_bytes"
        " FROM attempts"
        " WHERE k=? AND verdict='UNSAT' AND checker_verdict='VERIFIED'"
        " ORDER BY n_vertices ASC LIMIT ?",
        (k, limit),
    )
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]
