from typing import Dict, Any
import heapq
from .base import SearchBase, Node
from .astar import Heuristic


class GreedyBestFirst(SearchBase):
    def __init__(self, grid, heuristic=Heuristic.octile):
        super().__init__(grid)
        self.hf = heuristic
        sx, sy = grid.start
        gx, gy = grid.goal
        start = self.open[0]
        start.h = self.hf(gx - sx, gy - sy)
        start.f = start.h

    def step(self) -> Dict[str, Any]:
        if not self.open:
            return {"finished": True, "path": [], "stats": {"expanded": self.expanded}}
        cur = heapq.heappop(self.open)
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
            gx, gy = self.grid.goal
            h = self.hf(gx - nx, gy - ny)
            node = Node(f=h, x=nx, y=ny, g=cur.g + self.grid.move_cost((cur.x, cur.y), (nx, ny)), h=h, parent=(cur.x, cur.y))
            heapq.heappush(self.open, node)
            self.parent_map[(nx, ny)] = (cur.x, cur.y)
            neighbors.append((nx, ny))
        return self.snapshot((cur.x, cur.y), neighbors)
