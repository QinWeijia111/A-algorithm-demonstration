from dataclasses import dataclass, field
from typing import Tuple, Dict, Any, List, Optional, Set
import heapq


@dataclass(order=True)
class Node:
    f: float
    x: int = field(compare=False)
    y: int = field(compare=False)
    g: float = field(compare=False, default=0.0)
    h: float = field(compare=False, default=0.0)
    parent: Optional[Tuple[int, int]] = field(compare=False, default=None)


class SearchBase:
    def __init__(self, grid):
        self.grid = grid
        self.open: List[Node] = []
        self.open_map: Dict[Tuple[int, int], Node] = {}
        self.closed: Set[Tuple[int, int]] = set()
        self.parent_map: Dict[Tuple[int, int], Optional[Tuple[int, int]]] = {}
        sx, sy = grid.start
        n = Node(f=0.0, x=sx, y=sy, g=0.0, h=0.0, parent=None)
        heapq.heappush(self.open, n)
        self.open_map[(sx, sy)] = n
        self.parent_map[(sx, sy)] = None
        self.expanded = 0

    def reconstruct(self, xy: Tuple[int, int]) -> List[Tuple[int, int]]:
        path: List[Tuple[int, int]] = []
        cur: Optional[Tuple[int, int]] = xy
        visited: Set[Tuple[int, int]] = set()
        while cur is not None and cur not in visited:
            visited.add(cur)
            path.append(cur)
            cur = self.parent_map.get(cur)
        path.reverse()
        return path

    def snapshot(self, current: Tuple[int, int], neighbors: List[Tuple[int, int]], finished: bool = False) -> Dict[str, Any]:
        open_list = [((n.x, n.y), n.g, n.h, n.f) for n in self.open]
        closed_list = list(self.closed)
        payload: Dict[str, Any] = {
            "current": current,
            "neighbors": neighbors,
            "open": open_list[:500],
            "closed": closed_list[:500],
            "stats": {"expanded": self.expanded},
        }
        if finished:
            payload["finished"] = True
        return payload
