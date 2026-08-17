#!/usr/bin/env python3
"""Search for a better topology on one network-design instance.

    python scripts/solve.py 17 --seconds 900 --replicas 8 --start mixed

Writes a checker-format .sol file into results/ whenever the search ends with a
topology whose exact integral routing beats the published best-known value.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import time

import numpy as np

from qoblib_net import (BKV, CongestionOracle, lower_bounds, parse_demand,
                        parallel_tempering, read_topology, verify,
                        write_solution)

DEFAULT_QOBLIB = os.environ.get("QOBLIB_ROOT", os.path.expanduser("~/WORK/QOBLIB/repo"))


def reference_solution_path(root: str, n: int) -> str:
    for suffix in ("opt", "bst"):
        p = f"{root}/08-network/solutions/network{n:02d}.{suffix}.sol"
        if os.path.exists(p):
            return p
    raise FileNotFoundError(f"no reference solution for network{n:02d} under {root}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("n", type=int, help="instance size, 5..24")
    ap.add_argument("--seconds", type=float, default=600)
    ap.add_argument("--replicas", type=int, default=8)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--start", choices=["ref", "random", "mixed"], default="mixed")
    ap.add_argument("--qoblib", default=DEFAULT_QOBLIB,
                    help="path to a clone of ZIB-AOPT/QOBLIB")
    ap.add_argument("--outdir", default="results")
    a = ap.parse_args()

    demand_file = f"{a.qoblib}/08-network/instances/demand.txt"
    demand = parse_demand(demand_file, a.n)
    lb = lower_bounds(a.n, demand)
    ref_arcs = read_topology(reference_solution_path(a.qoblib, a.n))

    orc = CongestionOracle(a.n, demand)
    ref_energy = orc.energy(ref_arcs)
    print(f"network{a.n:02d}  published best-known {BKV[a.n]}  "
          f"(reference topology LP {ref_energy:.1f})  lower bound {lb['best']:.0f}")

    rng = np.random.default_rng(a.seed)
    if a.start == "ref":
        start = ref_arcs
    elif a.start == "random":
        start = None
    else:
        from qoblib_net.topology import random_topology
        start = [list(ref_arcs) if r % 2 == 0 else random_topology(a.n, rng)
                 for r in range(a.replicas)]

    t0 = time.time()

    def report(e, secs):
        print(f"  [{secs:7.1f}s] LP energy {e:12.1f}   "
              f"vs best-known {BKV[a.n]}  ({e - BKV[a.n]:+.1f})", flush=True)

    res = parallel_tempering(a.n, demand, seconds=a.seconds, replicas=a.replicas,
                             seed=a.seed, start=start, on_improve=report)
    print(f"search finished: {res['evals']} LP evaluations in {res['seconds']:.0f}s "
          f"({res['evals']/max(res['seconds'],1e-9):.0f}/s), {res['swaps']} replica swaps")

    os.makedirs(a.outdir, exist_ok=True)
    record = {"instance": f"network{a.n:02d}", "best_lp": res["energy"],
              "published_bkv": BKV[a.n], "lower_bound": lb["best"],
              "evals": res["evals"], "seconds": res["seconds"], "seed": a.seed,
              "start": a.start, "arcs": res["arcs"]}
    json.dump(record, open(f"{a.outdir}/network{a.n:02d}_seed{a.seed}.json", "w"), indent=1)

    # the routing must be integral, so ceil(LP) is what a topology can actually achieve
    achievable = math.ceil(res["energy"] - 1e-6)
    if achievable >= BKV[a.n]:
        print(f"no improvement (best achievable {achievable} >= {BKV[a.n]}); "
              f"nothing written for submission")
        return

    print("candidate improvement found - recovering an integral routing...")
    z, flows, col = orc.integral(res["arcs"], time_limit=600)
    if flows is None:
        print("integral routing failed; candidate is LP-only and NOT submittable")
        return
    path = f"{a.outdir}/network{a.n:02d}.sol"
    write_solution(path, a.n, res["arcs"], z, flows, col)
    ok, obj, msg = verify(path, a.n, demand)
    print(f"wrote {path}: verified={ok} objective={obj} ({msg})")
    if ok and obj < BKV[a.n]:
        print(f"*** IMPROVES the published best-known value: {obj} < {BKV[a.n]} ***")
        print("    Now re-check with the official Rust checker before submitting.")


if __name__ == "__main__":
    main()
