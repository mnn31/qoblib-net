"""Exact objective for QOBLIB problem 06 (multi-period portfolio optimization).

Reimplements the reference model of
``06-portfolio/models/binary_quadratic_programming/bqp_u3_c10.zpl`` in exact
rational arithmetic, matching the official Rust checker term by term including
Zimpl's ``round`` (half away from zero).  Every coefficient rounds to an
integer, so once they are built the whole objective is integer arithmetic.

State representation: a period is described by unit counts ``u[g]`` over the
2n *groups* ``g = (asset, direction)``, direction +1 long and -1 short.  This
is the same canonical form the checker's solution format uses.
"""

from __future__ import annotations

import gzip
import os
from fractions import Fraction

import numpy as np


def zround(x: Fraction) -> int:
    """Zimpl's round(): half away from zero, on an exact rational."""
    half = Fraction(1, 2)
    shifted = x - half if x < 0 else x + half
    # Fraction floor division truncates toward -inf, so emulate trunc()
    return int(shifted) if shifted >= 0 else -int(-shifted)


DEFAULTS = dict(cash=Fraction(1000000), unit=Fraction(100000),
                delta=Fraction(1, 1000), nu=Fraction(1, 10000),
                rho=Fraction(25, 1000000), ub=3, cs1=4, cs2=7,
                upscale=Fraction(1))


def _open(path):
    return gzip.open(path, "rt") if path.endswith(".gz") else open(path)


def _find(directory: str, stem: str) -> str:
    for cand in (f"{directory}/{stem}.txt.gz", f"{directory}/{stem}.txt"):
        if os.path.exists(cand):
            return cand
    raise FileNotFoundError(f"{stem} not found in {directory}")


class Instance:
    """Prices and covariances for one portfolio base directory."""

    def __init__(self, directory: str, params: dict | None = None):
        self.dir = directory
        self.p = dict(DEFAULTS)
        if params:
            self.p.update(params)

        raw: dict[str, dict[int, Fraction]] = {}
        order: list[str] = []
        for line in _open(_find(directory, "stock_prices")):
            line = line.split("#")[0].strip()
            if not line:
                continue
            t, sym, val = line.split()
            if sym not in raw:
                raw[sym] = {}
                order.append(sym)
            raw[sym][int(t)] = Fraction(val)

        self.symbols = order
        self.n = len(order)
        self.periods = max(raw[order[0]]) + 1
        unit = self.p["unit"]
        # one unit is `unit` of cash at t = 0, so prices are rebased there
        self.price = [[raw[s][t] * unit / raw[s][0] for t in range(self.periods)]
                      for s in self.symbols]

        idx = {s: i for i, s in enumerate(self.symbols)}
        self.cov: dict[tuple[int, int, int], Fraction] = {}
        for line in _open(_find(directory, "covariance_matrices")):
            line = line.split("#")[0].strip()
            if not line:
                continue
            t, a, b, val = line.split()
            if a in idx and b in idx:
                self.cov[(idx[a], idx[b], int(t))] = Fraction(val)

    # groups: index g -> (asset, tau).  Long group first, then short.
    @property
    def groups(self) -> list[tuple[int, int]]:
        return [(i, tau) for i in range(self.n) for tau in (1, -1)]


class Coefficients:
    """All rounded integer coefficients for one (instance, budget, lambda)."""

    def __init__(self, inst: Instance, budget: int, lam: Fraction):
        p = inst.p
        self.inst = inst
        self.budget = budget
        self.lam = lam
        self.groups = inst.groups
        G, T = len(self.groups), inst.periods
        self.T = T
        self.G = G
        self.t_end = T - 1
        self.capital = int(p["cash"] / p["unit"])
        self.ub = p["ub"]
        self.cs1, self.cs2 = p["cs1"], p["cs2"]

        # risk[t][a][b]
        self.risk = np.zeros((T, G, G), dtype=np.int64)
        if lam != 0:
            for t in range(T):
                for a, (i, ti) in enumerate(self.groups):
                    for b, (j, tj) in enumerate(self.groups):
                        c = inst.cov.get((i, j, t))
                        if c is None:
                            raise KeyError(f"missing covariance ({i},{j},{t})")
                        self.risk[t, a, b] = zround(
                            lam * (ti * tj) * c * inst.price[i][t] * inst.price[j][t])

        # short cost, transaction rate, return, all per group and period
        self.short = np.zeros((T, G), dtype=np.int64)
        self.delta = np.zeros((T, G), dtype=np.int64)
        self.ret = np.zeros((T, G), dtype=np.int64)
        for t in range(T):
            for a, (i, tau) in enumerate(self.groups):
                if tau == -1:
                    self.short[t, a] = zround(p["rho"] * inst.price[i][t])
                self.delta[t, a] = zround(p["delta"] * inst.price[i][t])
                if t < self.t_end:
                    self.ret[t, a] = zround(tau * (inst.price[i][t + 1] - inst.price[i][t]))

        self.cash = np.array(
            [zround(p["nu"] * p["unit"] * (1 << k)) for k in range(self.cs1)],
            dtype=np.int64)
        self.tau = np.array([tau for _, tau in self.groups], dtype=np.int64)

    # ------------------------------------------------------------------
    def enumerate_states(self) -> np.ndarray:
        """All feasible per-period unit-count vectors, as an (S, G) int array."""
        G, ub, B = self.G, self.ub, self.budget
        lo_total = max(0, B - ((1 << self.cs2) - 1))
        states: list[list[int]] = []
        cur = [0] * G

        def rec(g: int, remaining: int):
            if g == G:
                total = B - remaining
                if total < lo_total:
                    return
                net = int(sum(cur[a] * self.tau[a] for a in range(G)))
                slack = self.capital - net
                if 0 <= slack <= (1 << self.cs1) - 1:
                    states.append(list(cur))
                return
            for v in range(min(ub, remaining) + 1):
                cur[g] = v
                rec(g + 1, remaining - v)
            cur[g] = 0

        rec(0, B)
        return np.array(states, dtype=np.int64)

    def period_cost(self, t: int, U: np.ndarray) -> np.ndarray:
        """Everything in period t that depends only on that period's state."""
        cost = np.zeros(len(U), dtype=np.int64)
        if self.lam != 0:
            cost += np.einsum("sa,ab,sb->s", U, self.risk[t], U)
        cost += U @ self.short[t]
        if t < self.t_end:
            cost -= U @ self.ret[t]
        if t == 0:
            cost += U @ self.delta[0]
        if t == self.t_end:
            cost += U @ self.delta[self.t_end]
        net = U @ self.tau
        slack = self.capital - net
        for k in range(self.cs1):
            cost -= np.where((slack >> k) & 1, self.cash[k], 0)
        return cost

    def transition_cost(self, t: int, U: np.ndarray, chunk: int = 512):
        """Rebalancing cost from period t-1 to period t, as a generator of
        (row_slice, matrix) so large state sets never materialise at once."""
        d = self.delta[t]
        for lo in range(0, len(U), chunk):
            hi = min(lo + chunk, len(U))
            diff = np.abs(U[lo:hi, None, :] - U[None, :, :])
            yield slice(lo, hi), diff @ d
