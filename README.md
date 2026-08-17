# qoblib-net

Solvers for two [QOBLIB](https://zib-aopt.github.io/QOBLIB/) problem classes.

**Results so far**

| what | outcome |
| :--- | :--- |
| Problem 08, Network Design | 5 new best-known values (`network14`-`network18`), see [results/RESULTS.md](results/RESULTS.md) |
| Problem 06, Portfolio | 96 open instances closed to proven optimality, see [results/PORTFOLIO.md](results/PORTFOLIO.md) |

Everything is verified with QOBLIB's own checkers before it is written down.

---

## Problem 08, Network Design

Stochastic search for the
Bienstock–Günlük min-congestion network design problem from the
[Quantum Optimization Benchmarking Library](https://zib-aopt.github.io/QOBLIB/).

Build a digraph on `n` nodes where every node has in-degree and out-degree
exactly 2, route a fixed traffic matrix over it, and minimise the largest total
load on any arc. Instances `network05` … `network24`. Six are solved to proven
optimality; the other fourteen have stood as best-known upper bounds, and the
24-node case has resisted proof of optimality since 1995.

## The idea

The problem splits cleanly in two:

- **Outer**: which digraph? Combinatorial, enormous, no useful lower bound.
- **Inner**: given the digraph, how to route? A min-congestion multicommodity
  flow, which is a linear program and therefore exactly solvable in milliseconds.

So the search only ever moves over topologies, scoring each one with an exact
LP oracle. Two properties measured here make that work:

1. On all 20 published solutions, `ceil(LP)` equals the published objective
   exactly. The LP relaxation of the routing is tight, so the LP value is a
   sound search energy and integrality only has to be restored at the end.
2. A 2-in/2-out digraph is the union of two fixed-point-free permutations that
   disagree everywhere, and the 2-exchange `(a→b),(c→d) ⇒ (a→d),(c→b)`
   preserves every degree. Every proposal is feasible by construction.

That is exactly the setting simulated annealing and parallel tempering are for:
a rugged discrete landscape with a cheap exact energy and a natural
degree-preserving move set.

## Install

```bash
pip install -r requirements.txt
```

You also need a clone of the benchmark for the instance data:

```bash
git clone --depth 1 https://github.com/ZIB-AOPT/QOBLIB.git
export QOBLIB_ROOT=$PWD/QOBLIB
```

## Use

Re-verify every published solution and confirm the LP oracle agrees with all of
them. Run this first, it is the harness everything else rests on:

```bash
python scripts/check_reference.py
```

Search one instance:

```bash
python scripts/solve.py 17 --seconds 900 --replicas 8 --start mixed --seed 0
```

Survey the whole benchmark for remaining headroom:

```bash
python scripts/survey_qoblib.py
```

## Layout

| path | what it is |
|---|---|
| `qoblib_net/instance.py` | demand matrix, published best-known values, lower bounds |
| `qoblib_net/topology.py` | the 2-in/2-out digraph space and its degree-preserving moves |
| `qoblib_net/oracle.py` | exact min-congestion routing (LP for search, MIP for output) |
| `qoblib_net/search.py` | simulated annealing and parallel tempering |
| `qoblib_net/solio.py` | solution-file I/O and an independent feasibility checker |
| `scripts/` | verification harness, solver driver, benchmark survey |
| `docs/RESEARCH_NOTES.md` | where the headroom is across all ten QOBLIB classes |

## Verification

`qoblib_net.solio.verify` is a from-scratch re-implementation of the official
Rust checker (`08-network/check/src/main.rs`). It reproduces the published
objective for all 20 instances. It is a development convenience, **not** a
substitute. Run the official Rust checker before submitting anything upstream.

## Licence

Apache 2.0, matching the benchmark's code licence. The QOBLIB instance data is
CC BY 4.0 and is not vendored here.
