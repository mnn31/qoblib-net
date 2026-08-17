"""Exact dynamic program for QOBLIB problem 06.

The objective couples periods only through the rebalancing term between
consecutive periods, and the reference model charges no rebalancing into the
final period.  So the whole thing is a chain: given the set of feasible
per-period portfolios, the optimum follows from one forward pass, and the last
period detaches entirely.

That structure is invisible to a MIP or QUBO solver working on the flat model,
which is why instances that time out there can be closed exactly here.
"""

from __future__ import annotations

from fractions import Fraction

import numpy as np

from .model import Coefficients, Instance


def read_canonical(path: str):
    """Parse the checker's canonical solution format.

    Returns (headers, {(period, symbol): (long, short)}).
    """
    headers, pos = {}, {}
    for line in open(path):
        line = line.split("#")[0].strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) == 2:
            headers[parts[0]] = parts[1]
        elif len(parts) == 4:
            t, sym, lo, sh = parts
            pos[(int(t), sym)] = (int(lo), int(sh))
        else:
            raise ValueError(f"unparsable line: {line!r}")
    return headers, pos


def counts_to_matrix(coef: Coefficients, pos) -> np.ndarray:
    """Positions dict -> (T, G) count matrix."""
    inst = coef.inst
    idx = {s: i for i, s in enumerate(inst.symbols)}
    U = np.zeros((coef.T, coef.G), dtype=np.int64)
    for (t, sym), (lo, sh) in pos.items():
        i = idx[sym]
        U[t, 2 * i] = lo
        U[t, 2 * i + 1] = sh
    return U


def objective(coef: Coefficients, U: np.ndarray) -> int:
    """Objective of a full (T, G) schedule, integer, matching the checker."""
    total = 0
    for t in range(coef.T):
        total += int(coef.period_cost(t, U[t:t + 1])[0])
        if 0 < t < coef.t_end:
            total += int(np.abs(U[t] - U[t - 1]) @ coef.delta[t])
    return total


def solve_exact(coef: Coefficients, chunk: int = 512, verbose: bool = False):
    """Exact minimum over all feasible schedules.  Returns (value, (T, G) array)."""
    U = coef.enumerate_states()
    S = len(U)
    if verbose:
        print(f"  {S} feasible per-period portfolios, {coef.T} periods")

    # the last period carries no rebalancing coupling, so it detaches
    last = coef.period_cost(coef.t_end, U)
    best_last = int(last.min())
    arg_last = int(last.argmin())

    if coef.T == 1:
        out = np.zeros((1, coef.G), dtype=np.int64)
        out[0] = U[arg_last]
        return best_last, out

    f = coef.period_cost(0, U).astype(np.int64)
    back = np.zeros((coef.t_end, S), dtype=np.int32)
    for t in range(1, coef.t_end):
        cost_t = coef.period_cost(t, U)
        nxt = np.empty(S, dtype=np.int64)
        arg = np.empty(S, dtype=np.int32)
        for sl, trans in coef.transition_cost(t, U, chunk=chunk):
            # trans[r, s] is the cost of moving from state s to state sl.start+r
            tot = trans + f[None, :]
            nxt[sl] = tot.min(axis=1)
            arg[sl] = tot.argmin(axis=1)
        f = nxt + cost_t
        back[t] = arg

    end_prev = int(f.argmin())
    value = int(f[end_prev]) + best_last

    out = np.zeros((coef.T, coef.G), dtype=np.int64)
    out[coef.t_end] = U[arg_last]
    s = end_prev
    for t in range(coef.t_end - 1, -1, -1):
        out[t] = U[s]
        if t > 0:
            s = int(back[t][s])
    return value, out


def write_canonical(path: str, coef: Coefficients, U: np.ndarray, instance_name: str,
                    lam_text: str, value: int, comment: str = "") -> None:
    lines = []
    if comment:
        lines += [f"# {c}" for c in comment.splitlines()]
    lines += [f"instance {instance_name}",
              f"budget {coef.budget}",
              f"lambda {lam_text}",
              f"objective {value}",
              "# period symbol long short"]
    syms = coef.inst.symbols
    for t in range(coef.T):
        for i, sym in enumerate(syms):
            lo, sh = int(U[t, 2 * i]), int(U[t, 2 * i + 1])
            if lo or sh:
                lines.append(f"{t} {sym} {lo} {sh}")
    open(path, "w").write("\n".join(lines) + "\n")


LAMBDA_GRID = ["0", "0.000001", "0.00001", "0.00005", "0.0001",
               "0.0005", "0.001", "0.01"]

#: how QOBLIB names the lambda part of an instance id
LAMBDA_TAG = {"0": "l0", "0.000001": "l1e-06", "0.00001": "l1e-05",
              "0.00005": "l5e-05", "0.0001": "l1e-04", "0.0005": "l5e-04",
              "0.001": "l1e-03", "0.01": "l1e-02"}


def lam_fraction(text: str) -> Fraction:
    return Fraction(text)
