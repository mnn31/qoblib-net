"""Heuristics for QOBLIB problem 08, Network Design.

Layout:
    instance   -- demand matrix, published best-known values, lower bounds
    topology   -- the 2-in/2-out digraph search space and its moves
    oracle     -- exact min-congestion routing for a fixed topology
    search     -- simulated annealing and parallel tempering over topologies
    solio      -- solution-file I/O and an independent feasibility checker
"""

from .instance import BKV, INTSCALE, PROVEN_OPTIMAL, lower_bounds, parse_demand
from .oracle import CongestionOracle
from .search import anneal, parallel_tempering
from .solio import read_topology, verify, write_solution

__all__ = [
    "BKV", "INTSCALE", "PROVEN_OPTIMAL", "lower_bounds", "parse_demand",
    "CongestionOracle", "anneal", "parallel_tempering",
    "read_topology", "verify", "write_solution",
]
