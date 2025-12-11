import math
from backend.algorithms.grid import Grid
from backend.algorithms.astar import AStar, Heuristic
from backend.algorithms.llm_astar import LLMAStar


def run_all(algo):
    last = None
    for _ in range(10000):
        snap = algo.step()
        last = snap
        if snap.get('finished'):
            return snap
    return last


def test_llm_astar_works_without_api_key():
    g = Grid(10, set(), (0, 0), (9, 9), True)
    a = AStar(g, heuristic=Heuristic.octile, weight=1.0)
    l = LLMAStar(g, heuristic=Heuristic.octile, weight=1.0)
    sa = run_all(a)
    sl = run_all(l)
    assert sa['finished'] and sl['finished']
    assert math.isclose(sa['stats']['cost'], sl['stats']['cost'], rel_tol=1e-6)
