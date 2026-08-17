#!/usr/bin/env python3
"""Survey the whole QOBLIB benchmark: where is there still headroom?

Pulls the published site data and reports, per problem class, how many
instances are proven optimal, how many only have a best-known upper bound, and
how many are still completely open (no feasible solution on record).  Open
instances are the cheapest place to earn a leaderboard record, since any valid
feasible solution becomes the first entry.

    python scripts/survey_qoblib.py            # summary table
    python scripts/survey_qoblib.py --open 06  # list the open instances of a class
"""

from __future__ import annotations

import argparse
import collections
import json
import urllib.request

DATA_URL = "https://zib-aopt.github.io/QOBLIB/data/instances.json"


def load(url: str = DATA_URL):
    with urllib.request.urlopen(url) as fh:
        return json.load(fh)


def summarise(data) -> None:
    header = f"{'#':<4}{'Problem':<30}{'instances':>10}{'optimal':>9}{'best-known':>12}{'open':>7}"
    print(header)
    print("-" * len(header))
    totals = collections.Counter()
    for p in data["problems"]:
        c = collections.Counter(i.get("status", "?") for i in p["instances"])
        totals.update(c)
        n = len(p["instances"])
        print(f"{p['id']:<4}{p['name']:<30}{n:>10}{c.get('optimal', 0):>9}"
              f"{c.get('best_known', 0):>12}{c.get('open', 0):>7}")
    print("-" * len(header))
    print(f"{'':<34}{sum(totals.values()):>10}{totals['optimal']:>9}"
          f"{totals['best_known']:>12}{totals['open']:>7}")


def list_open(data, problem_id: str) -> None:
    for p in data["problems"]:
        if p["id"] != problem_id:
            continue
        rows = [i for i in p["instances"] if i.get("status") == "open"]
        print(f"{p['id']} {p['name']}: {len(rows)} open instances")
        for i in rows:
            m = i.get("metrics") or {}
            extra = " ".join(f"{k}={v}" for k, v in m.items())
            print(f"  {i['name']:<40} {extra}")
        return
    raise SystemExit(f"no problem with id {problem_id!r}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--open", metavar="ID", help="list the open instances of one class")
    ap.add_argument("--url", default=DATA_URL)
    a = ap.parse_args()
    data = load(a.url)
    if a.open:
        list_open(data, a.open)
    else:
        summarise(data)


if __name__ == "__main__":
    main()
