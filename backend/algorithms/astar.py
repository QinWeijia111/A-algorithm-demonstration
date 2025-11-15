from typing import Tuple, List, Dict, Any
import math
import heapq
from .base import SearchBase, Node


class Heuristic:
    @staticmethod
    def zero(dx: int, dy: int) -> float:
        return 0.0

    @staticmethod
    def manhattan(dx: int, dy: int) -> float:
        return abs(dx) + abs(dy)

    @staticmethod
    def euclidean(dx: int, dy: int) -> float:
        return math.sqrt(dx * dx + dy * dy)

    @staticmethod
    def octile(dx: int, dy: int) -> float:
        a, b = abs(dx), abs(dy)
        return a + b + (math.sqrt(2) - 2.0) * min(a, b)

    @staticmethod
    def chebyshev(dx: int, dy: int) -> float:
        return max(abs(dx), abs(dy))


class AStar(SearchBase):
    def __init__(self, grid, heuristic=Heuristic.octile, weight: float = 1.0):
        super().__init__(grid)
        self.hf = heuristic
        self.weight = weight
        gx, gy = grid.goal
        # initialize f of start
        sx, sy = grid.start
        h0 = self.hf(gx - sx, gy - sy)
        start = self.open[0]
        start.h = h0
        start.f = start.g + self.weight * h0
        self.open_map[(sx, sy)] = start
    
    def step(self) -> Dict[str, Any]:
        if not self.open:
            return {"finished": True, "path": [], "stats": {"expanded": self.expanded}}
        cur = heapq.heappop(self.open)
        self.open_map.pop((cur.x, cur.y), None)
        self.closed.add((cur.x, cur.y))
        self.expanded += 1
        if (cur.x, cur.y) == self.grid.goal:
            path = self.reconstruct((cur.x, cur.y))
            snap = self.snapshot((cur.x, cur.y), [], finished=True)
            snap["path"] = path
            snap["stats"]["cost"] = cur.g
            return snap
        neighbors = []
        for nx, ny in self.grid.neighbors(cur.x, cur.y):
            if (nx, ny) in self.closed:
                continue
            tentative_g = cur.g + self.grid.move_cost((cur.x, cur.y), (nx, ny))
            node = self.open_map.get((nx, ny))
            gx, gy = self.grid.goal
            h = self.hf(gx - nx, gy - ny)
            f = tentative_g + self.weight * h
            if node is None:
                node = Node(f=f, x=nx, y=ny, g=tentative_g, h=h, parent=(cur.x, cur.y))
                heapq.heappush(self.open, node)
                self.open_map[(nx, ny)] = node
                self.parent_map[(nx, ny)] = (cur.x, cur.y)
            elif tentative_g < node.g:
                node.g = tentative_g
                node.h = h
                node.f = f
                node.parent = (cur.x, cur.y)
                heapq.heapify(self.open)
                self.parent_map[(nx, ny)] = (cur.x, cur.y)
            neighbors.append((nx, ny))
        return self.snapshot((cur.x, cur.y), neighbors)

