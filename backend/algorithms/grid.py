from typing import Set, Tuple, List
import math


class Grid:
    def __init__(self, size: int, obstacles: Set[Tuple[int, int]], start: Tuple[int, int], goal: Tuple[int, int], diagonal: bool = True):
        self.size = size
        self.obstacles = obstacles
        self.start = start
        self.goal = goal
        self.diagonal = diagonal

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.size and 0 <= y < self.size

    def is_free(self, x: int, y: int) -> bool:
        return (x, y) not in self.obstacles

    def neighbors(self, x: int, y: int) -> List[Tuple[int, int]]:
        dirs4 = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        dirs8 = dirs4 + [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        dirs = dirs8 if self.diagonal else dirs4
        res = []
        for dx, dy in dirs:
            nx, ny = x + dx, y + dy
            if self.in_bounds(nx, ny) and self.is_free(nx, ny):
                res.append((nx, ny))
        return res

    def move_cost(self, from_xy: Tuple[int, int], to_xy: Tuple[int, int]) -> float:
        fx, fy = from_xy
        tx, ty = to_xy
        diag = abs(tx - fx) == 1 and abs(ty - fy) == 1
        return math.sqrt(2) if diag else 1.0

