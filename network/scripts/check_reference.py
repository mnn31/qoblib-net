#!/usr/bin/env python3
"""Sanity harness: re-verify every published network-design solution.

Confirms three things before any search is trusted:
  1. the independent checker reproduces the published objective exactly,
  2. the min-congestion LP on the published topology matches that objective
     (i.e. the reference routings are already optimal for their topology, and
     the LP relaxation is tight enough to use as a search energy),
  3. the cheap combinatorial lower bounds, for context.

    python scripts/check_reference.py --qoblib ~/WORK/QOBLIB/repo
"""

from __future__ import annotations

import argparse
import math
import os

from qoblib_net import (BKV, PROVEN_OPTIMAL, CongestionOracle, lower_bounds,
                        parse_demand, read_topology, verify)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--qoblib", default=os.environ.get(
        "QOBLIB_ROOT", os.path.expanduser("~/WORK/QOBLIB/repo")))
    a = ap.parse_args()

    demand_file = f"{a.qoblib}/08-network/instances/demand.txt"
    head = (f"{'instance':<11}{'published':>11}{'checker':>10}{'LP(topology)':>14}"
            f"{'lower bnd':>11}{'gap to LB':>11}  status")
    print(head)
    print("-" * len(head))
    all_ok = True
    for n in range(5, 25):
        demand = parse_demand(demand_file, n)
        suffix = "opt" if n in PROVEN_OPTIMAL else "bst"
        path = f"{a.qoblib}/08-network/solutions/network{n:02d}.{suffix}.sol"
        ok, obj, msg = verify(path, n, demand)
        arcs = read_topology(path)
        lp = CongestionOracle(n, demand).energy(arcs)
        lb = lower_bounds(n, demand)["best"]
        agree = ok and obj == BKV[n] and math.ceil(lp - 1e-6) == BKV[n]
        all_ok &= agree
        print(f"network{n:02d}{BKV[n]:>11}{obj:>10}{lp:>14.1f}{lb:>11.0f}"
              f"{(BKV[n]-lb)/BKV[n]*100:>10.1f}%  "
              f"{'ok' if agree else 'MISMATCH: ' + msg}")
    print("-" * len(head))
    print("all published solutions reproduced" if all_ok else "DISCREPANCIES FOUND")


if __name__ == "__main__":
    main()
