# Results

## New best-known values, problem 08 (Network Design)

Nine instances improved over the values published in
`08-network/solutions/0-info.txt`. Every solution below has been verified by the
official Rust checker (`08-network/check`, exit code 0) and independently by
`qoblib_net.solio.verify`.

| instance | published best-known | this work | improvement | relative |
| :--- | ---: | ---: | ---: | ---: |
| network14 | 350,173 | **350,167** | 6 | 0.00% |
| network15 | 383,000 | **376,000** | 7,000 | 1.83% |
| network16 | 409,067 | **405,834** | 3,233 | 0.79% |
| network17 | 460,182 | **440,834** | 19,348 | 4.20% |
| network18 | 481,950 | **475,656** | 6,294 | 1.31% |
| network19 | 514,625 | **500,773** | 13,852 | 2.69% |
| network20 | 548,536 | **533,904** | 14,632 | 2.67% |
| network21 | 593,000 | **581,591** | 11,409 | 1.92% |
| network23 | 686,453 | **662,576** | 23,877 | 3.48% |

Solution files are in `results/best/`, in the Gurobi `.sol` format the checker
parses.

For context, the only community submission on record for this problem class is a
2-hour Gurobi 11 run on a 64-thread AMD EPYC 7542, and it does not reach the
published reference values on any of these instances. The runs above used one
core of a laptop for 25 to 40 minutes each.

### Official checker output

```
network14 : Computed maximum flow: 350167 / VALID: Solution successfully verified
network15 : Computed maximum flow: 376000 / VALID: Solution successfully verified
network16 : Computed maximum flow: 405834 / VALID: Solution successfully verified
network17 : Computed maximum flow: 440834 / VALID: Solution successfully verified
network18 : Computed maximum flow: 475656 / VALID: Solution successfully verified
network19 : Computed maximum flow: 500773 / VALID: Solution successfully verified
network20 : Computed maximum flow: 533904 / VALID: Solution successfully verified
network21 : Computed maximum flow: 581591 / VALID: Solution successfully verified
network23 : Computed maximum flow: 662576 / VALID: Solution successfully verified
```

The same checker was run on the published reference solutions as a control and
returned their published objectives exactly, so the harness is not the source of
the difference.

### How they were found

Parallel tempering over 2-in/2-out digraphs. Eight replicas on a geometric
temperature ladder from 6% to 0.2% of the incumbent energy, degree-preserving
2-exchanges as the move, replica exchange every 40 proposals. Half the replicas
started from the published reference topology and half from random topologies.
Each replica's energy is the exact min-congestion multicommodity flow LP for its
topology. One run per instance, single core, on an Apple M-series laptop.

The integral routing was recovered once at the end by re-solving the same model
with integrality on the flow variables. In every case the integral optimum
equalled `ceil(LP)`, consistent with the tightness observed across all 20
published solutions.

### Not improved

`network11`, `network12` and `network13` were run under the same settings, twice
each with different seeds, and matched their published values exactly without
beating them. Those three look like strong local optima or possibly true optima,
even though only `network05` to `network10` are proven.

`network24` was deliberately not targeted. Its continuous-flow twin is MIPLIB
2017's `dano3mip`, whose best-known value was set in 2022 with Gurobi's NoRel
heuristic warm-started from the previous record. That one is defended by the
people who write the solvers.

`network22` produced a candidate at 624,790 against a published 647,594, but the
run crashed while serialising its topology and the arc set was lost. It is being
re-run rather than reported.

### Reproducing

```bash
python scripts/solve.py 17 --seconds 1500 --replicas 8 --seed 7 --start mixed
```

A stochastic result needs more than one run before it can be submitted. QOBLIB
requires at least 5 independent runs with seeds documented, so a full sweep
(`scripts/sweep.py`) is the unit of work that goes upstream, not any single run.
