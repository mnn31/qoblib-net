# Problem 06, Portfolio Optimization: 160 instances solved exactly

Every instance of the `a003`, `a004` and `a005` families was listed as **open**
on the QOBLIB leaderboard, meaning no feasible solution was on record at all.
All 96 of them (12 instance bases times the 8-value lambda grid) are now solved
to **proven optimality**, and all 96 pass the official checker
(`06-portfolio/check`, exit code 0).

The same dynamic program was then run on the `a010_t10` and `a010_t15`
families, 64 more instances. Every value matches the published one exactly, so
nothing improves there, but they are now **proven optimal** rather than
best-known. 50 of those 64 were listed as best-known only.

| family | instances | published status before | after |
| :--- | ---: | :--- | :--- |
| a003, a004, a005 | 96 | open, no solution on record | proven optimal |
| a010_t10 | 32 | 8 optimal, 24 best-known | 32 proven optimal |
| a010_t15 | 32 | 6 optimal, 26 best-known | 32 proven optimal |

All 160 pass the official checker. Solutions are in `results/portfolio/` and
`results/portfolio_a010/`, in the checker's canonical format.

That the DP agrees with all 64 published `a010` values is worth stating plainly:
it is the strongest available evidence that the implementation is right, since
those values come from independent solver runs on the shipped LP and QUBO
models.

Submitted upstream as https://github.com/ZIB-AOPT/QOBLIB/pull/44.

## Why they were open, and why they are easy

Nothing about them is hard. No LP or QUBO model files are shipped for these
families, only for `a010` and `a050`, so there was nothing for a solver to be
pointed at. The instance data was always there.

## The method

The reference model couples periods in exactly one place: the rebalancing term
between consecutive periods. Everything else, the risk quadratic, the return,
the short-selling cost, the cash interest on the slack register, is a function
of a single period's portfolio. The model also charges no rebalancing into the
final period, only liquidation.

So the problem is a chain, and the optimum follows from one forward dynamic
program over per-period portfolios:

```
f_0(s)      = cost_0(s)
f_t(s)      = cost_t(s) + min_s' [ f_{t-1}(s') + rebalance_t(s', s) ]    0 < t < T-1
optimum     = min_s f_{T-2}(s) + min_s cost_{T-1}(s)
```

A per-period portfolio is a vector of unit counts over the 2n (asset,
direction) groups, subject to the budget and capital slack registers. For these
families that is 84 to 991 states, so the DP runs in well under a second.

This structure is invisible to a MIP or QUBO solver working on the flat binary
model, which is the interesting part: instances that a general solver has to
branch on are closed exactly by exploiting the chain.

Total compute: **6 seconds** for the 96 small instances. The `a010`
families have 10,606 feasible portfolios per period, so those take a few
minutes each and were run across three workers.

## Validation

Three separate checks, in order of how much they are worth:

1. The objective implementation was validated against the shipped reference
   solutions. It reproduces the published objective **exactly** on every
   `a010` solution tested, including the bit-exact Zimpl `round` behaviour
   (half away from zero on exact rationals).
2. The DP was validated against instances whose published values are marked
   proven optimal. On `po_a010_t10_orig` it returned the published optimum for
   lambda = 0, 1e-5 and 1e-6 exactly.
3. All 96 emitted solutions were verified by the official Rust checker, which
   recomputes the objective in exact rational arithmetic and confirms the
   claimed value.

Only after all three did any of these get written down.

## Example

```
$ check_portfolio instances/po_a005_t04_s02 results/portfolio/a005_t04_s02_b004_l1e-04.sol
t= 0: net=  -2 total=   4 cash_slack=  12 count_slack=   0  ok
t= 1: net=  -1 total=   3 cash_slack=  11 count_slack=   1  ok
t= 2: net=  -4 total=   4 cash_slack=  14 count_slack=   0  ok
t= 3: net=   0 total=   0 cash_slack=  10 count_slack=   4  ok
Objective breakdown:
  risk                       10209
  return                    -26052
  transaction                 1184
  cash interest               -470
  short cost                    22
  liquidation                    0
Objective value = -15107
Claimed objective matches.
Solution successfully verified
```

## Reproducing

```bash
python scripts/portfolio_solve.py --bases a003,a004,a005 --outdir results/portfolio
```
