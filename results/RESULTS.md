# Results

## New best-known values, problem 08 (Network Design)

Five instances improved over the values published in
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

Solution files are in `results/best/`, in the Gurobi `.sol` format the checker
parses.

### Official checker output

```
network14 : Computed maximum flow: 350167 / VALID: Solution successfully verified
network15 : Computed maximum flow: 376000 / VALID: Solution successfully verified
network16 : Computed maximum flow: 405834 / VALID: Solution successfully verified
network17 : Computed maximum flow: 440834 / VALID: Solution successfully verified
network18 : Computed maximum flow: 475656 / VALID: Solution successfully verified
```

The same checker was run on the five published reference solutions as a control
and returned their published objectives exactly, so the harness is not the
source of the difference.

### How they were found

Parallel tempering over 2-in/2-out digraphs. Eight replicas on a geometric
temperature ladder from 6% to 0.2% of the incumbent energy, degree-preserving
2-exchanges as the move, replica exchange every 40 proposals. Half the replicas
started from the published reference topology and half from random topologies.
Each replica's energy is the exact min-congestion multicommodity flow LP for its
topology. One 25-minute run per instance, single core each, seed 7, on an Apple
M-series laptop.

Evaluation counts for that run:

| instance | LP evaluations | wall clock |
| :--- | ---: | ---: |
| network14 | 221,250 | 25 min |
| network15 | 173,897 | 25 min |
| network16 | 138,661 | 25 min |
| network17 | 112,618 | 25 min |
| network18 | 91,810 | 25 min |

The integral routing was recovered once at the end by re-solving the same model
with integrality on the flow variables. In all five cases the integral optimum
equalled `ceil(LP)`, which is consistent with the tightness observed across all
20 published solutions.

### Not improved

`network11`, `network12` and `network13` were run under identical settings and
matched their published values exactly without beating them. That is a useful
signal: those three look like strong local optima, or possibly optimal, even
though only `network05` to `network10` are proven.

### Reproducing

```bash
python scripts/solve.py 17 --seconds 1500 --replicas 8 --seed 7 --start mixed
```

A stochastic result needs more than one run before it can be submitted. QOBLIB
requires at least 5 independent runs with seeds documented, so the numbers above
are a finding, not yet a submission. Use `scripts/sweep.py` for the run set.
