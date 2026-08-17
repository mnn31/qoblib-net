# Plan

Three tracks, ordered by how certain the payoff is. They are independent — a
failure on one costs nothing on the others.

## Track A — verification harness (done)

`scripts/check_reference.py` reproduces the published objective for all 20
network-design instances and confirms the LP oracle agrees with every one of
them. This is the foundation: without it, no search result can be trusted, and
with it, any claimed improvement can be self-checked before it goes anywhere.

Status: passing on all 20.

## Track B — the network-design search (the research contribution)

Target: `network11` … `network23`. Deliberately **not** `network24`.

Reason: the 24-node continuous-flow version is MIPLIB 2017's `dano3mip`, one of
the most-attacked open instances in mixed-integer programming. Its best-known
value (664.0208) was set by Michael Winkler in 2022 with Gurobi's NoRel
heuristic warm-started from the previous record, which itself came from ParaSCIP
in 2014. That record is defended by the people who write the solvers.

`network11`–`network23` are QOBLIB-specific truncations of the same matrix. They
are *not* in MIPLIB and have nothing like that history. Their published values
come from the same curated reference set, but nobody has run a dedicated
metaheuristic at them — the only community submission on record is a 2-hour
Gurobi baseline that loses to the reference on every single one, by up to 15%.

Steps:

1. Parallel tempering across the 13 instances, seeded both from random
   topologies and from the reference topology. Multiple seeds each.
2. If any run beats the published value: recover an integral routing, verify
   locally, then build the Rust checker and verify officially before claiming
   anything.
3. Whatever the outcome, write it up. The QOBLIB contribution guide accepts
   feasible-but-suboptimal submissions and explicitly asks for negative results,
   so a careful "here is how annealing and replica exchange scale on this
   problem class, here is where they plateau relative to the 30-year reference"
   is a legitimate merged submission with full method metadata.

Calibration: 2 minutes of naive single-chain SA on `network11` lands 7.5% above
the record. So this is a real search problem, not a formality.

## Track C — open instances (the high-certainty play)

333 of QOBLIB's 1,264 instances have **no feasible solution on record at all**.
On those, the first valid submission takes the record outright — no incumbent to
beat. Ranked by effort:

- **`06-portfolio`, `a003`/`a004`/`a005` (12 bases × 8 λ values).** A few dozen
  binary variables each. No LP or QUBO model files are shipped for them, which
  is almost certainly why they were never solved — the model has to be generated
  first, from `models/binary_quadratic_programming/bqp_u3_c10.zpl`. Once
  generated these are small enough to solve to proven optimality outright.
- **`06-portfolio`, `a200`/`a400` (16 bases × 8 λ).** Same missing-model
  situation, but 18,000 binaries at `a200_t15`. Feasible solutions are easy to
  construct (the constraints are two equalities per period); good ones are not.
  This is where a p-bit / annealing approach has room.
- **`05-sports` (102 open)** — read the warning first: those instances were
  selected *because* existing solvers could not find any feasible solution in
  reasonable time. High risk, high reward.
- **`04-steiner` (147 open)** — the largest open surface, but instances run to
  millions of variables. A sequential rip-up-and-reroute heuristic is the
  standard attack.

Do not touch `02-labs` (records held by a decade of dedicated tabu search) or
`10-topology` (Graph Golf, its own long-running competition, integer-valued
objective).

## Submission mechanics

Read `CONTRIBUTING.md` in the benchmark repo before the first PR. The parts that
bite:

- Every PR needs approval from **two committee members**, so expect a wait.
- `Optimality Bound` must stay `N/A` for heuristic runs — setting it equal to
  the objective asserts a proven optimum and triggers a hard check.
- At least 5 independent runs for a stochastic method, 10+ recommended, seeds
  documented.
- The optional objective time series is CI-enforced monotone; a minimisation run
  whose incumbent ever increases is a hard failure that blocks the merge.
- The official Rust checker (`08-network/check/`) needs `cargo`, which is not
  installed here. Install Rust before the first real submission.
