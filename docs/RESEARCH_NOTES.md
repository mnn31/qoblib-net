# QOBLIB: where the headroom actually is

Notes from a full read of the benchmark, the paper, and the repository, plus a
measurement pass over the published data. Everything numeric here was checked
against a local clone of `ZIB-AOPT/QOBLIB` and the site's published JSON, not
taken from the website copy.

## 1. What QOBLIB is (and is not)

QOBLIB, the Quantum Optimization Benchmarking Library, is a curated set of ten
NP-hard problem classes maintained by the Zuse Institute Berlin together with
IBM Quantum, published in *Nature Computational Science* (2026) and on arXiv as
`2504.03832`. It came out of the Quantum Optimization Working Group started by
IBM Quantum in July 2023.

It is **not** a timed contest. There is no entry fee, no registration, no
deadline, and no prize. It is a rolling, permanently open benchmark:

- You submit by opening a **pull request** against the GitHub repository with a
  canonical CSV plus your solution files.
- CI runs `misc/ci/check_submission.py`; a red run blocks the merge.
- On merge, `.github/workflows/update-bkv.yml` recomputes each instance's
  best-known value and credits the **first** source to reach it.
- The public leaderboard shows, per instance, the record and who holds it.

Two consequences worth internalising:

1. **A submission does not have to win.** The contribution guide is explicit
   that feasible-but-suboptimal solutions are accepted, and that reporting
   negative results is welcome. Every merged submission is listed with its full
   method metadata. So a rigorous benchmarking study is publishable here even if
   it sets no records.
2. **A record requires strictly improving the previous best.** Matching it
   credits nobody, because attribution goes to whoever got there first.

Current scale: 1,264 instances, ~2,600 submissions, 24 contributing
organisations (IBM and ZIB dominate).

## 2. The headroom map

Pulled from `https://zib-aopt.github.io/QOBLIB/data/instances.json` and
cross-checked against each class's `solutions/README.md`
(reproduce with `scripts/survey_qoblib.py`):

| # | Problem class | instances | proven optimal | best-known only | **fully open** |
|---|---|---:|---:|---:|---:|
| 01 | Market Split | 156 | 115 | 0 | **41** |
| 02 | LABS | 99 | 65 | 34 | 0 |
| 03 | Min. Birkhoff Decomposition | 375 | 66 | 294 | **15** |
| 04 | Steiner Tree Packing | 190 | 29 | 14 | **147** |
| 05 | Sports Tournament Scheduling | 249 | 147 | 0 | **102** |
| 06 | Portfolio Optimization | 44 | 0 | 16 | **28** |
| 07 | Maximum Independent Set | 50 | 39 | 11 | 0 |
| 08 | Network Design | 20 | 6 | 14 | 0 |
| 09 | Vehicle Routing | 55 | 54 | 1 | 0 |
| 10 | Topology Design | 26 | 12 | 14 | 0 |
| | **total** | **1264** | **533** | **398** | **333** |

"Open" means *no feasible solution is on record at all*. On an open instance,
the first valid feasible submission becomes the record outright, with no need to
beat anybody.

### Reading the classes

- **02 LABS**: the 34 non-optimal instances are n = 67..100, where the standing
  values come from the Packebusch–Mertens exhaustive/memetic line of work.
  Those records have held for a decade against dedicated tabu search. Avoid.
- **10 Topology Design**: this is Graph Golf, which has run as its own public
  competition for years; the objective is a small integer diameter, so an
  improvement means dropping it by a whole unit. Avoid.
- **03 Birkhoff**: 294 best-known entries were swept in a single submission
  (`20260805_BirkhoffPlus_Valls`) days before these notes. Soft class, but the
  bar was just raised across the board and a competitor is clearly active.
- **06 Portfolio**: four independent submissions (Gurobi, Abs2, Arvak, ISQR)
  and *none* improved a reference value, which says the curated references are
  strong. But 28 of 44 bases are open, including both the trivial ones
  (`a003`/`a004`/`a005`, a few dozen binaries) and the large ones
  (`a200`/`a400`), and no LP/QUBO models are shipped for either group.
- **04 Steiner (147 open)** and **05 Sports (102 open)** are the two biggest
  open surfaces. Note the sports README's warning: the open instances were
  selected precisely *because* existing solvers could not find any feasible
  solution in reasonable time. Steiner's open instances run to millions of
  variables.
- **08 Network Design**: analysed in detail below.

## 3. Problem 08 in detail

### The problem

Given the fixed 24x24 traffic matrix `T` and `p = 2`, build a simple digraph on
`n` nodes where every node has in-degree and out-degree exactly 2, then route
`t[i][j]` units from `i` to `j` for all pairs, minimising the largest total load
on any arc. Instance `networkNN` uses the leading `NN x NN` block of `T`; all
demands are scaled by 1000 and the flows must be integral.

This is Bienstock–Günlük (1995). The QOBLIB paper states plainly that the
24-node case "has been withstanding all attempts to solve it to proven
optimality for the last 30 years," and the continuous-flow variant is a MIPLIB
2017 instance.

### The published baseline is weak, and that is the opening

`08-network/submissions/20250102_Gurobi_Schicker/` holds a Gurobi 11 run,
2-hour limit, AMD EPYC 7542 with 64 threads. Its own numbers:

| instance | Gurobi 2h | Gurobi bound | MIP gap | reference best-known |
|---|---:|---:|---:|---:|
| network10 | 210,800 | 202,750 | 3.8% | 210,800 |
| network13 | 313,000 | 248,974 | 20.5% | **304,116** |
| network17 | 488,699 | 280,281 | 42.7% | **460,182** |
| network20 | 570,974 | 351,740 | 38.4% | **548,536** |
| network23 | 749,923 | 349,579 | 53.4% | **686,453** |
| network24 | 779,410 | 224,386 | 71.2% | **663,688** |

Two things follow. First, the lower bounds are hopeless, so proving
optimality is off the table and this is purely an upper-bound race. Second, **two hours of
64-thread Gurobi loses to the curated reference on every open instance**, by up
to 15%. The references are not solver output; they are the accumulated residue
of thirty years of specialised work. That is a real bar, but it is a bar set by
*heuristics*, which is the fair fight.

### Why this class suits a stochastic-search project

Measured here, not assumed:

- **The problem factorises.** Choose the topology (combinatorial, brutal);
  given the topology, the routing is a min-congestion multicommodity flow, which is a
  linear program. So a metaheuristic only ever has to search over digraphs,
  with an exact oracle scoring each one.
- **The LP relaxation of the routing is tight.** On all 20 published
  topologies, `ceil(LP)` equals the published objective exactly (see
  `scripts/check_reference.py`). So the LP value is a legitimate search energy,
  and the integral routing only has to be recovered once at the end.
- **The oracle is fast.** 1.8 ms per evaluation at n = 11, 10 ms at n = 17,
  34 ms at n = 24, so roughly 550, 100 and 30 evaluations per second on one core.
- **The state space has a clean neighbourhood.** A 2-in/2-out digraph is the
  union of two fixed-point-free permutations that disagree everywhere. The
  2-exchange `(a→b),(c→d) ⇒ (a→d),(c→b)` preserves all four degrees, so every
  proposal is feasible by construction and only strong connectivity needs
  re-checking. That is exactly the structure simulated annealing and parallel
  tempering want.
- **The instances are small.** n ≤ 24, 48 arcs. This runs on a laptop. No GPU,
  no cluster, no commercial solver licence.

### Calibration

Naive single-chain SA from a random start, 2 minutes on one core, network11:
reaches 256,182 against a best-known of 238,334, which is 7.5% short. So the records
are genuinely non-trivial and a serious method is required. That is the right
difficulty for a research project: not free, not hopeless.

The cheap combinatorial lower bounds (half the largest row/column sum; total
demand over 2n arcs) sit 24–55% below the best-known values on the open
instances, so they give context but no useful stopping criterion.

## 4. Practical notes for submitting

- Solution format is Gurobi `.sol`: a `z` line, then `x#i#j` for every ordered
  pair, then `f#k#i#j` flow values. Flows and `z` are in units of 1/1000.
- The official checker is Rust (`08-network/check/`) and needs `cargo`, which is
  not installed on this machine. `qoblib_net.solio.verify` re-implements it
  independently and reproduces all 20 published objectives, but the Rust checker
  must still be run before opening a PR.
- The CSV template is `misc/submission_template.csv`. Required fields that are
  easy to forget: variable-type counts, non-zero coefficient count and range,
  `Paradigm` (Classical / Quantum Simulator / Quantum Hardware), `# Runs`,
  `# Feasible Runs`, `# Successful Runs`, the success threshold ε, and full
  hardware specifications.
- For stochastic methods the guide requires at least 5 independent runs and
  recommends 10+, with seeds documented.
- Leave `Optimality Bound` as `N/A` for heuristic runs. Setting it equal to
  `Best Objective Value` asserts a proven optimum and triggers a hard check.
- The optional objective time series (`<instance>_objective_time_series.json`)
  enables time-to-solution analysis. CI enforces monotonicity, so a minimisation
  run whose incumbent ever increases is a hard failure.

## 5. Sources

- QOBLIB site and data: https://zib-aopt.github.io/QOBLIB/
- Repository: https://github.com/ZIB-AOPT/QOBLIB
- Koch et al., *The Quantum Optimization Benchmarking Library*, Nature
  Computational Science 6, 653–671 (2026), doi:10.1038/s43588-026-00991-1
- arXiv preprint 2504.03832, *Quantum Optimization Benchmarking Library: The
  Intractable Decathlon*
- Bienstock & Günlük, *Computational experience with a difficult mixed-integer
  multicommodity flow problem*, Mathematical Programming 68, 213–237 (1995)
