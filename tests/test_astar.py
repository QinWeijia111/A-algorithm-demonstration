import math
from backend.algorithms.grid import Grid
from backend.algorithms.astar import AStar, Heuristic
from backend.algorithms.dijkstra import Dijkstra


def run_all(algo):
    last = None
    for _ in range(10000):
        snap = algo.step()
        last = snap
        if snap.get('finished'):
            return snap
    return last


def test_astar_equals_dijkstra_on_zero_heuristic():
    g = Grid(10, set(), (0, 0), (9, 9), True)
    a0 = AStar(g, heuristic=Heuristic.zero, weight=0.0)
    d = Dijkstra(g)
    sa = run_all(a0)
    sd = run_all(d)
    assert sa['finished'] and sd['finished']
    assert math.isclose(sa['stats']['cost'], sd['stats']['cost'], rel_tol=1e-6)

