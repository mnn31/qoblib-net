"""The search space: simple digraphs on n nodes with in-degree = out-degree = 2.

Such a digraph is exactly the union of two fixed-point-free permutations that
disagree everywhere (no self-loops, no repeated arc), which makes uniform
sampling easy and gives a natural degree-preserving neighbourhood.
"""

from __future__ import annotations

import numpy as np

Arc = tuple[int, int]


def arcs_from_perms(s1: np.ndarray, s2: np.ndarray) -> list[Arc]:
    n = len(s1)
    return [(i, int(s1[i])) for i in range(n)] + [(i, int(s2[i])) for i in range(n)]


def is_strongly_connected(n: int, arcs) -> bool:
    fwd = [[] for _ in range(n)]
    bwd = [[] for _ in range(n)]
    for i, j in arcs:
        fwd[i].append(j)
        bwd[j].append(i)

    def reaches_all(adj):
        seen = {0}
        stack = [0]
        while stack:
            u = stack.pop()
            for v in adj[u]:
                if v not in seen:
                    seen.add(v)
                    stack.append(v)
        return len(seen) == n

    return reaches_all(fwd) and reaches_all(bwd)


def random_topology(n: int, rng: np.random.Generator, tries: int = 10_000) -> list[Arc]:
    """Rejection-sample a strongly connected 2-in/2-out digraph."""
    for _ in range(tries):
        s1 = rng.permutation(n)
        if np.any(s1 == np.arange(n)):
            continue
        s2 = rng.permutation(n)
        if np.any(s2 == np.arange(n)) or np.any(s2 == s1):
            continue
        arcs = arcs_from_perms(s1, s2)
        if is_strongly_connected(n, arcs):
            return sorted(arcs)
    raise RuntimeError(f"failed to sample a topology for n={n}")


def double_swap(arcs: list[Arc], rng: np.random.Generator):
    """Degree-preserving 2-exchange:  (a->b), (c->d)  becomes  (a->d), (c->b).

    Out-degrees of a and c and in-degrees of b and d are all unchanged, so the
    result is still 2-in/2-out.  Returns ``None`` when the swap would create a
    self-loop or a duplicate arc.
    """
    m = len(arcs)
    p, q = rng.integers(0, m, size=2)
    if p == q:
        return None
    a, b = arcs[p]
    c, d = arcs[q]
    if a == d or c == b or b == d:
        return None
    s = set(arcs)
    if (a, d) in s or (c, b) in s:
        return None
    new = list(arcs)
    new[p] = (a, d)
    new[q] = (c, b)
    return new


def triple_swap(arcs: list[Arc], rng: np.random.Generator):
    """Degree-preserving 3-exchange: rotate the heads of three arcs.

    (a->b), (c->d), (e->f)  becomes  (a->d), (c->f), (e->b).  Escapes local
    optima that every 2-exchange leaves intact.
    """
    m = len(arcs)
    p, q, r = rng.choice(m, size=3, replace=False)
    (a, b), (c, d), (e, f) = arcs[p], arcs[q], arcs[r]
    if len({b, d, f}) < 3:
        return None
    if a == d or c == f or e == b:
        return None
    s = set(arcs)
    if (a, d) in s or (c, f) in s or (e, b) in s:
        return None
    new = list(arcs)
    new[p] = (a, d)
    new[q] = (c, f)
    new[r] = (e, b)
    return new


def propose(arcs, rng, p_triple: float = 0.15):
    return triple_swap(arcs, rng) if rng.random() < p_triple else double_swap(arcs, rng)
