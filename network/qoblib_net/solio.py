"""Read/write QOBLIB solution files, plus an independent feasibility checker.

``verify`` is a from-scratch re-implementation of
``08-network/check/src/main.rs``.  It exists so results can be checked without a
Rust toolchain; it is not a substitute for the official checker, which should
still be run before anything is submitted upstream.
"""

from __future__ import annotations

import numpy as np

from .instance import INTSCALE


def read_topology(path: str) -> list[tuple[int, int]]:
    """Extract the arc set (0-indexed) from a solution file."""
    arcs = []
    for line in open(path):
        t = line.split()
        if len(t) == 2 and t[0].startswith("x#") and t[1] == "1":
            _, i, j = t[0].split("#")
            arcs.append((int(i) - 1, int(j) - 1))
    return sorted(arcs)


def write_solution(path: str, n: int, arcs, z: float, flow_vec, col_index) -> None:
    """Emit a Gurobi-format .sol file in the layout the official checker parses.

    The declared objective is recomputed from the flows rather than taken from
    the solver's z variable.  The model only constrains z >= every arc load, so
    a solver may return a z that is not tight; the checker compares the declared
    value against the largest arc load it computes itself and rejects any
    mismatch.  Recomputing keeps the two in step and can only lower the reported
    objective.
    """
    arcset = set(arcs)
    load = {}
    for (k, ai), c in col_index.items():
        u, v = arcs[ai]
        val = int(round(flow_vec[c]))
        if val and k != v:
            load[(u, v)] = load.get((u, v), 0) + val
    z_true = max(load.values()) if load else 0
    out = ["# Solution for model obj",
           f"# Objective value = {z_true}",
           f"z {z_true}"]
    for i in range(1, n + 1):
        for j in range(n, 0, -1):
            if i == j:
                continue
            out.append(f"x#{i}#{j} {1 if (i - 1, j - 1) in arcset else 0}")
    for (k, ai), c in col_index.items():
        u, v = arcs[ai]
        val = int(round(flow_vec[c]))
        if val:
            out.append(f"f#{k+1}#{u+1}#{v+1} {val}")
    open(path, "w").write("\n".join(out) + "\n")


def verify(path: str, n: int, demand: np.ndarray):
    """Independent feasibility check.  Returns (ok, objective, message)."""
    x, f, z = {}, {}, None
    for line in open(path):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        tok = line.split()
        if len(tok) != 2:
            return False, -1, f"unparsable line: {line!r}"
        name, val = tok[0], int(tok[1])
        if name == "z":
            z = val
        elif name.startswith("x#"):
            _, i, j = name.split("#")
            x[(int(i), int(j))] = val
        elif name.startswith("f#"):
            _, k, i, j = name.split("#")
            f[(int(k), int(i), int(j))] = val
    if z is None:
        return False, -1, "no objective variable z in file"

    for i in range(1, n + 1):
        if sum(x.get((i, j), 0) for j in range(1, n + 1) if j != i) != 2:
            return False, -1, f"out-degree != 2 at node {i}"
        if sum(x.get((j, i), 0) for j in range(1, n + 1) if j != i) != 2:
            return False, -1, f"in-degree != 2 at node {i}"

    for k in range(1, n + 1):
        for i in range(1, n + 1):
            if i == k:
                continue
            fin = sum(f.get((k, j, i), 0) for j in range(1, n + 1) if j != i)
            fout = sum(f.get((k, i, j), 0)
                       for j in range(1, n + 1) if j != i and j != k)
            if fin - fout != demand[k - 1][i - 1] * INTSCALE:
                return False, -1, f"flow conservation violated: commodity {k}, node {i}"

    for (k, i, j), v in f.items():
        if v and not x.get((i, j), 0):
            return False, -1, f"flow on arc ({i},{j}) which is not in the topology"

    worst = 0
    for i in range(1, n + 1):
        for j in range(1, n + 1):
            if i == j:
                continue
            load = sum(f.get((k, i, j), 0) for k in range(1, n + 1) if k != j)
            worst = max(worst, load)
    if worst != z:
        return False, worst, f"declared z={z} but the largest arc load is {worst}"
    return True, worst, "valid"
