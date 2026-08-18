#!/usr/bin/env python3
"""Solve QOBLIB problem 06 instances exactly with the chain dynamic program.

    python scripts/portfolio_solve.py --bases a003,a004,a005 --outdir results/portfolio

Each (base, lambda) pair is one QOBLIB instance id, e.g. a004_t04_s01_b004_l1e-04.
The DP is exact, so every value produced here is a proven optimum for the
reference model, not a heuristic bound.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from fractions import Fraction

from qoblib_portfolio.model import Coefficients, Instance
from qoblib_portfolio.solver import (LAMBDA_GRID, LAMBDA_TAG, objective,
                                     solve_exact, write_canonical)

QOBLIB = os.environ.get("QOBLIB_ROOT", os.path.expanduser("~/WORK/QOBLIB/repo"))
BUDGET_BY_ASSETS = {3: 3, 4: 4, 5: 4, 10: 4, 50: 20, 200: 50, 400: 100}


def bases_for(prefixes: list[str]) -> list[str]:
    root = f"{QOBLIB}/06-portfolio/instances"
    out = []
    for d in sorted(os.listdir(root)):
        if not d.startswith("po_"):
            continue
        if any(d.startswith(f"po_{p}") for p in prefixes):
            out.append(d)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bases", default="a003,a004,a005",
                    help="comma-separated instance-name prefixes")
    ap.add_argument("--lambdas", default=",".join(LAMBDA_GRID))
    ap.add_argument("--outdir", default="results/portfolio")
    ap.add_argument("--chunk", type=int, default=512)
    a = ap.parse_args()

    os.makedirs(a.outdir, exist_ok=True)
    lams = a.lambdas.split(",")
    records = []

    for base in bases_for(a.bases.split(",")):
        inst = Instance(f"{QOBLIB}/06-portfolio/instances/{base}")
        budget = BUDGET_BY_ASSETS[inst.n]
        short = base[3:]                       # strip the "po_" prefix
        print(f"{base}: {inst.n} assets, {inst.periods} periods, B={budget}")
        for lam_text in lams:
            iid = f"{short}_b{budget:03d}_{LAMBDA_TAG[lam_text]}"
            coef = Coefficients(inst, budget, Fraction(lam_text))
            t0 = time.time()
            value, U = solve_exact(coef, chunk=a.chunk)
            dt = time.time() - t0
            assert objective(coef, U) == value, "schedule does not reproduce its own value"
            path = f"{a.outdir}/{iid}.sol"
            write_canonical(path, coef, U, base, lam_text, value,
                            comment="exact optimum, chain dynamic program over "
                                    "per-period portfolios")
            print(f"    {iid:<32} optimum {value:>10}   [{dt:.1f}s]")
            records.append({"instance": iid, "base": base, "budget": budget,
                            "lambda": lam_text, "objective": value,
                            "proven_optimal": True, "seconds": dt,
                            "solution": os.path.basename(path)})

    json.dump(records, open(f"{a.outdir}/summary.json", "w"), indent=1)
    print(f"\n{len(records)} instances solved to proven optimality")


if __name__ == "__main__":
    main()
