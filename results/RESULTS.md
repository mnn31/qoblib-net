# Results

## New best-known values, problem 08 (Network Design)

Ten of the fourteen open instances improved over the values published in
`08-network/solutions/0-info.txt`. Every solution has been verified by the
official Rust checker (`08-network/check`, exit code 0) and independently by
`qoblib_net.solio.verify`.

| instance | published best-known | this work | improvement | relative |
| :--- | ---: | ---: | ---: | ---: |
| network14 | 350,173 | **342,455** | 7,718 | 2.20% |
| network15 | 383,000 | **372,500** | 10,500 | 2.74% |
| network16 | 409,067 | **401,000** | 8,067 | 1.97% |
| network17 | 460,182 | **434,429** | 25,753 | 5.60% |
| network18 | 481,950 | **475,656** | 6,294 | 1.31% |
| network19 | 514,625 | **497,000** | 17,625 | 3.42% |
| network20 | 548,536 | **526,653** | 21,883 | 3.99% |
| network21 | 593,000 | **569,554** | 23,446 | 3.95% |
| network22 | 647,594 | **621,810** | 25,784 | 3.98% |
| network23 | 686,453 | **660,000** | 26,453 | 3.85% |

Solution files are in `results/best/`, in the Gurobi `.sol` format the checker
parses.

For scale: the only community submission on record for this problem class is a
2-hour Gurobi 11 run on a 64-thread AMD EPYC 7542, and it fails to reach the
published reference values on any of these instances, by up to 15%. The runs
here used one core of a laptop for 20 to 40 minutes each.

Note that `network23` now sits below `network24` (660,000 against 663,688),
which is the ordering the demand data suggests it should have had all along:
node 24 contributes little traffic but two more arcs in each direction, so the
24-node instance has more routing freedom than the 23-node one.

### Method

Parallel tempering over 2-in/2-out digraphs. Eight replicas on a geometric
temperature ladder from 6% to 0.2% of the incumbent energy; moves are
degree-preserving 2- and 3-exchanges on the arc set, so every proposal is
feasible by construction and only strong connectivity has to be rechecked;
replica exchange every 40 proposals. A replica's energy is the exact
min-congestion multicommodity flow LP for its topology. Half the replicas start
from the published reference topology and half from random topologies.

The integral routing is recovered once at the end by re-solving the same model
with integrality on the flow variables. In every case the integral optimum
equalled `ceil(LP)`, consistent with the tightness observed across all 20
published solutions.

### Run statistics

Five to seven independent runs per instance across three waves, 20 to 40 minutes
each, single core per run, seeds documented in `results/sweep/` and
`results/run_stats.json`.

| instance | runs | runs reaching the best value |
| :--- | ---: | ---: |
| network14 | 6 | 1 |
| network15 | 6 | 1 |
| network16 | 6 | 1 |
| network17 | 6 | 1 |
| network18 | 6 | 1 |
| network19 | 6 | 1 |
| network20 | 6 | 1 |
| network21 | 6 | 1 |
| network22 | 5 | 1 |
| network23 | 6 | 1 |

One run in each set reaches the best value found, which says the landscape is
rugged and that a single run understates what the method can do. Adding seeds
kept helping throughout: `network14` improved from 350,167 on a single early run
to 342,455 once six runs were pooled.

### Not improved

`network11`, `network12` and `network13` were run seven times each and matched
their published values exactly every time without beating them. Those three look
like strong local optima or true optima, even though only `network05` to
`network10` are proven.

`network24` was deliberately not targeted. Its continuous-flow twin is MIPLIB
2017's `dano3mip`, whose best-known value was set in 2022 with Gurobi's NoRel
heuristic warm-started from the previous record, which itself came from ParaSCIP
in 2014. That record is defended by the people who write the solvers.

### Reproducing

```bash
python scripts/sweep.py --instances 11-23 --seeds 5 --seconds 1200 --workers 8
```
