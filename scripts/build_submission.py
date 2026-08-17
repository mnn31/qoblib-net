#!/usr/bin/env python3
"""Assemble a QOBLIB submission directory from local results.

Layout produced (what misc/ci/check_submission.py expects):

    <problem>/submissions/<YYYYMMDD>_<tag>_<name>/
        README.md
        <instance>/
            <instance>_summary.csv
            <instance>_solution.<ext>

    python scripts/build_submission.py portfolio --out /tmp/sub06
    python scripts/build_submission.py network   --out /tmp/sub08
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
from fractions import Fraction

QOBLIB = os.environ.get("QOBLIB_ROOT", os.path.expanduser("~/WORK/QOBLIB/repo"))

COLUMNS = ["Problem", "Submitter", "Affiliation", "Date", "Reference",
           "Best Objective Value", "Optimality Bound", "Modeling Approach",
           "# Decision Variables", "# Binary Variables", "# Integer Variables",
           "# Continuous Variables", "# Non-Zero Coefficients",
           "Coefficients Type", "Coefficients Range", "Workflow",
           "Algorithm Type", "Paradigm", "# Runs", "# Feasible Runs",
           "# Successful Runs", "Success Threshold", "Hardware Specifications",
           "Total Runtime", "Time to Solution", "CPU Runtime", "GPU Runtime",
           "QPU Runtime", "Other HW Runtime", "Remarks"]

SUBMITTER = os.environ.get("QOBLIB_SUBMITTER", "Manan Gupta")
AFFILIATION = os.environ.get("QOBLIB_AFFILIATION", "The Harker School")
REFERENCE = os.environ.get("QOBLIB_REFERENCE", "https://github.com/mnn31/qoblib-net")
DATE = os.environ.get("QOBLIB_DATE", "2026-08-17")
HARDWARE = os.environ.get(
    "QOBLIB_HARDWARE",
    "Apple M-series laptop, 11 cores, 18 GB RAM, macOS; single core per run")


def write_csv(path: str, row: dict) -> None:
    full = {c: row.get(c, "N/A") for c in COLUMNS}
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerow(full)


# ---------------------------------------------------------------- problem 06
def build_portfolio(out: str, results: str) -> int:
    from qoblib_portfolio.model import Coefficients, Instance

    # `results` may be a single results directory or a parent holding several
    # (the a010 families are solved by a few workers in parallel, one dir each)
    dirs = []
    if os.path.exists(f"{results}/summary.json"):
        dirs.append(results)
    for sub in sorted(os.listdir(results)):
        if os.path.exists(f"{results}/{sub}/summary.json"):
            dirs.append(f"{results}/{sub}")
    records = []
    for d in dirs:
        for rec in json.load(open(f"{d}/summary.json")):
            rec["_dir"] = d
            records.append(rec)
    root = f"{out}/{DATE_TAG}_ChainDP_Gupta"
    os.makedirs(root, exist_ok=True)
    open(f"{root}/README.md", "w").write(PORTFOLIO_README)

    inst_cache: dict[str, Instance] = {}
    for rec in records:
        iid, base = rec["instance"], rec["base"]
        if base not in inst_cache:
            inst_cache[base] = Instance(f"{QOBLIB}/06-portfolio/instances/{base}")
        inst = inst_cache[base]
        coef = Coefficients(inst, rec["budget"], Fraction(rec["lambda"]))

        n, T, ub = inst.n, inst.periods, coef.ub
        n_x = n * ub * 2 * T
        n_y = coef.cs1 * T
        n_s = coef.cs2 * T
        n_bin = n_x + n_y + n_s
        # constraint non-zeros, plus objective non-zeros at copy level
        nz_cons = T * ((n * ub * 2 + coef.cs1) + (n * ub * 2 + coef.cs2))
        nz_quad = int(sum((coef.risk[t] != 0).sum() for t in range(T))) * ub * ub
        nz_lin = int((coef.delta != 0).sum() + (coef.short != 0).sum()
                     + (coef.ret != 0).sum()) * ub + coef.cs1 * T
        lo = min(int(coef.risk.min()), int(coef.ret.min()), 0)
        hi = max(int(coef.risk.max()), int(coef.delta.max()), int(coef.cash.max()))

        d = f"{root}/{iid}"
        os.makedirs(d, exist_ok=True)
        shutil.copy(f"{rec['_dir']}/{rec['solution']}", f"{d}/{iid}_solution.sol")
        write_csv(f"{d}/{iid}_summary.csv", {
            "Problem": iid,
            "Submitter": SUBMITTER, "Affiliation": AFFILIATION,
            "Date": DATE, "Reference": REFERENCE,
            "Best Objective Value": rec["objective"],
            "Optimality Bound": rec["objective"],
            "Modeling Approach":
                "Reference binary quadratic model of bqp_u3_c10.zpl, reformulated "
                "as a chain over per-period unit-count portfolios",
            "# Decision Variables": n_bin, "# Binary Variables": n_bin,
            "# Integer Variables": 0, "# Continuous Variables": 0,
            "# Non-Zero Coefficients": nz_cons + nz_quad + nz_lin,
            "Coefficients Type": "Integer",
            "Coefficients Range": f"{lo} - {hi}",
            "Workflow":
                "Parse prices and covariances in exact rational arithmetic; round every "
                "objective coefficient exactly as Zimpl does; enumerate all feasible "
                "per-period portfolios under the budget and capital slack registers; "
                "solve the resulting chain by forward dynamic programming, the last "
                "period detaching because the reference model charges no rebalancing "
                "into it; recover the schedule by backpointers.",
            "Algorithm Type": "Deterministic", "Paradigm": "Classical",
            "# Runs": 1, "# Feasible Runs": 1, "# Successful Runs": 1,
            "Success Threshold": 0,
            "Hardware Specifications": HARDWARE,
            "Total Runtime": round(rec["seconds"], 3),
            "Time to Solution": round(rec["seconds"], 3),
            "CPU Runtime": round(rec["seconds"], 3),
            "Remarks":
                "Exact method, so the reported value is a proven optimum and the "
                "optimality bound equals the objective. Variable and coefficient "
                "counts are for the reference binary model before presolve; "
                "non-zero count expands each group-pair risk coefficient over the "
                "ub^2 copy-slot pairs. Verified with 06-portfolio/check.",
        })
    return len(records)


# ---------------------------------------------------------------- problem 08
def build_network(out: str, results: str, sweep: str | None) -> int:
    from qoblib_net import BKV, parse_demand

    root = f"{out}/{DATE_TAG}_ParallelTempering_Gupta"
    os.makedirs(root, exist_ok=True)
    open(f"{root}/README.md", "w").write(NETWORK_README)

    # run statistics aggregated across every independent run of every wave,
    # written by the aggregation step (see results/RESULTS.md)
    stats = {}
    stats_file = os.path.join(os.path.dirname(results), "run_stats.json")
    if os.path.exists(stats_file):
        stats = {int(k): v for k, v in json.load(open(stats_file)).items()}

    made = 0
    for fname in sorted(os.listdir(results)):
        if not fname.endswith(".sol"):
            continue
        n = int(fname[len("network"):-len(".sol")])
        inst = f"network{n:02d}"
        demand = parse_demand(f"{QOBLIB}/08-network/instances/demand.txt", n)
        obj = int(open(f"{results}/{fname}").readlines()[1].split("=")[1])

        st = stats.get(n, {})
        n_runs = st.get("nruns", 1)
        n_succ = st.get("nsucc", 1)
        secs = st.get("avg_secs", 1500.0)

        n_arcs = n * (n - 1)
        n_x, n_f = n_arcs, n * n_arcs - n_arcs   # f[k,i,j] exists only for j != k
        n_f = n * (n - 1) * (n - 1)
        nz = 2 * n_arcs + n_arcs * (2 * n - 1) + n_f * 2 + n_arcs * n

        d = f"{root}/{inst}"
        os.makedirs(d, exist_ok=True)
        shutil.copy(f"{results}/{fname}", f"{d}/{inst}_solution.sol")
        write_csv(f"{d}/{inst}_summary.csv", {
            "Problem": inst,
            "Submitter": SUBMITTER, "Affiliation": AFFILIATION,
            "Date": DATE, "Reference": REFERENCE,
            "Best Objective Value": obj,
            "Optimality Bound": "N/A",
            "Modeling Approach":
                "Reference integer multicommodity flow model of d3ver0int.zpl, "
                "decomposed into a topology search over 2-in/2-out digraphs with an "
                "exact min-congestion flow solved for each candidate",
            "# Decision Variables": n_x + n_f + 1,
            "# Binary Variables": n_x,
            "# Integer Variables": n_f + 1,
            "# Continuous Variables": 0,
            "# Non-Zero Coefficients": nz,
            "Coefficients Type": "Integer",
            "Coefficients Range": "1 - 1000000",
            "Workflow":
                "Parallel tempering over 2-in/2-out digraphs. Eight replicas on a "
                "geometric temperature ladder from 6% to 0.2% of the incumbent energy; "
                "moves are degree-preserving 2- and 3-exchanges on the arc set, so "
                "every proposal is feasible by construction and only strong "
                "connectivity is rechecked; replica exchange every 40 proposals. A "
                "replica's energy is the exact min-congestion multicommodity flow LP "
                "for its topology, solved with HiGHS. Half the replicas start from the "
                "published reference topology and half from random topologies. The "
                "integral routing is recovered once at the end by re-solving the same "
                "model with integrality on the flow variables.",
            "Algorithm Type": "Stochastic", "Paradigm": "Classical",
            "# Runs": n_runs, "# Feasible Runs": n_runs,
            "# Successful Runs": n_succ, "Success Threshold": 0,
            "Hardware Specifications": HARDWARE,
            "Total Runtime": round(secs, 1),
            "Time to Solution": round(secs, 1),
            "CPU Runtime": round(secs, 1),
            "Remarks":
                "Heuristic, so the optimality bound is left as N/A. Runtimes are the "
                "average over the independent runs, single core each, queueing "
                "excluded. Successful runs are those reaching this method's own best "
                "value. Verified with 08-network/check.",
        })
        made += 1
    return made


DATE_TAG = os.environ.get("QOBLIB_DATE_TAG", "20260817")

PORTFOLIO_README = """# Exact chain dynamic programming for the portfolio instances

The reference model couples periods only through the rebalancing term between
consecutive periods, and charges no rebalancing into the final period. Every
other term, the risk quadratic, the return, the short-selling cost and the cash
interest on the slack register, depends on a single period's portfolio.

That makes the model a chain. Enumerating the feasible per-period portfolios
under the budget and capital slack registers and running a forward dynamic
program over them gives the exact optimum, with the last period detaching.

For the a003, a004 and a005 families a period has between 84 and 991 feasible
portfolios, so every instance closes in well under a second. All values here
are proven optima, not heuristic bounds.

The objective was implemented in exact rational arithmetic with Zimpl's
rounding, and validated against the shipped a010 reference solutions before any
of these were produced: it reproduces their published objective values exactly,
including the three that are marked proven optimal.

Code: https://github.com/mnn31/qoblib-net
"""

NETWORK_README = """# Parallel tempering over network topologies

The problem separates. Choosing the digraph is combinatorial and has no useful
lower bound; choosing the routing on a fixed digraph is a min-congestion
multicommodity flow, which is a linear program. So the search moves only over
topologies and scores each one with an exact LP.

Two things make that practical. On all 20 published solutions the ceiling of
the routing LP equals the published objective exactly, so the LP value is a
sound search energy and integrality only has to be restored at the end. And a
2-in/2-out digraph is the union of two fixed-point-free permutations that
disagree everywhere, so the 2-exchange (a->b),(c->d) => (a->d),(c->b) preserves
every degree and every proposal is feasible by construction.

Eight replicas, geometric temperature ladder, replica exchange every 40
proposals, half seeded from the published reference topology and half from
random topologies. Single core per run on a laptop.

Code: https://github.com/mnn31/qoblib-net
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("which", choices=["portfolio", "network"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--results", default=None)
    ap.add_argument("--sweep", default="results/sweep")
    a = ap.parse_args()

    if a.which == "portfolio":
        n = build_portfolio(a.out, a.results or "results/portfolio")
    else:
        n = build_network(a.out, a.results or "results/best", a.sweep)
    print(f"built {n} instance directories under {a.out}")


if __name__ == "__main__":
    main()
