from typing import Dict, Any
from .astar import AStar, Heuristic


class Dijkstra(AStar):
    def __init__(self, grid):
        super().__init__(grid, heuristic=Heuristic.zero, weight=0.0)

