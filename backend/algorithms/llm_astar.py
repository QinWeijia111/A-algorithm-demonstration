from typing import Tuple, List, Dict, Any, Optional
import math
import heapq
import os
import json
import re
import urllib.request
import urllib.error

from .base import SearchBase, Node
from .astar import Heuristic
try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

# load .env from this algorithms directory if available
_ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
if load_dotenv and os.path.exists(_ENV_PATH):
    load_dotenv(_ENV_PATH)


class LLMWaypointProvider:
    def __init__(self, model: str = "deepseek"):
        self.model = model
        # Prefer user-requested names, fallback to previous ones
        self.api_key = os.getenv("LLM_API_KEY", os.getenv("DEEPSEEK_API_KEY", ""))
        self.base_url = os.getenv("LLM_BASE_URL", os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))
        self.chat_url = f"{self.base_url}/v1/chat/completions"

    @staticmethod
    def _compress_barriers(obstacles: set, size: int) -> Tuple[List[List[int]], List[List[int]]]:
        horizontal: List[List[int]] = []
        vertical: List[List[int]] = []
        # rows
        for y in range(size):
            xs = sorted([x for (x, yy) in obstacles if yy == y])
            if not xs:
                continue
            start = xs[0]
            prev = xs[0]
            for x in xs[1:]:
                if x == prev + 1:
                    prev = x
                else:
                    horizontal.append([y, start, prev])
                    start = x
                    prev = x
            horizontal.append([y, start, prev])
        # cols
        for x in range(size):
            ys = sorted([y for (xx, y) in obstacles if xx == x])
            if not ys:
                continue
            start = ys[0]
            prev = ys[0]
            for y in ys[1:]:
                if y == prev + 1:
                    prev = y
                else:
                    vertical.append([x, start, prev])
                    start = y
                    prev = y
            vertical.append([x, start, prev])
        return horizontal[:200], vertical[:200]

    @staticmethod
    def _build_prompt(start: Tuple[int, int], goal: Tuple[int, int], hbars: List[List[int]], vbars: List[List[int]]) -> str:
        return (
            "Identify a path between the start and goal points to navigate around obstacles and find the shortest path to the goal.\n"
            "Horizontal barriers are represented as [y, x_start, x_end], and vertical barriers are represented as [x, y_start, y_end].\n"
            "Conclude your response with the generated path in the format \"Generated Path: [[x1, y1], [x2, y2], ...]\".\n\n"
            f"Start Point: [{start[0]}, {start[1]}]\n"
            f"Goal Point: [{goal[0]}, {goal[1]}]\n"
            f"Horizontal Barriers: {hbars}\n"
            f"Vertical Barriers: {vbars}\n"
            "Generated Path: "
        )

    @staticmethod
    def _parse_path(text: str) -> List[Tuple[int, int]]:
        lists = re.findall(r"\[\[.*?\]\]", text, re.DOTALL)
        if not lists:
            return []
        s = lists[-1]
        try:
            arr = json.loads(s)
        except Exception:
            try:
                import ast
                arr = ast.literal_eval(s)
            except Exception:
                return []
        res: List[Tuple[int, int]] = []
        for item in arr:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                try:
                    res.append((int(item[0]), int(item[1])))
                except Exception:
                    continue
        return res

    def _ask(self, prompt: str, max_tokens: int = 600) -> str:
        if not self.api_key:
            return ""
        payload = {
            "model": os.getenv("LLM_MODEL_ID", os.getenv("DEEPSEEK_MODEL", "deepseek-chat")),
            "messages": [
                {"role": "system", "content": (
                    "You are a path planning assistant. Return only the path as a list of coordinate pairs at the end, prefixed with 'Generated Path:'."
                )},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
            "max_tokens": max_tokens,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.chat_url,
            data=data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = resp.read().decode("utf-8")
                j = json.loads(body)
                return j.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception:
            return ""

    def get_waypoints(self, grid) -> List[Tuple[int, int]]:
        start = grid.start
        goal = grid.goal
        hbars, vbars = self._compress_barriers(grid.obstacles, grid.size)
        prompt = self._build_prompt(start, goal, hbars, vbars)
        out = self._ask(prompt) if (self.model == "deepseek") else ""
        pts = self._parse_path(out) if out else []
        # filter & enforce bounds
        filtered: List[Tuple[int, int]] = []
        for (x, y) in pts:
            if 0 <= x < grid.size and 0 <= y < grid.size and (x, y) not in grid.obstacles:
                filtered.append((x, y))
        if not filtered or filtered[0] != start:
            filtered.insert(0, start)
        if filtered[-1] != goal:
            filtered.append(goal)
        return filtered[:32]


class LLMAStar(SearchBase):
    def __init__(self, grid, heuristic=Heuristic.octile, weight: float = 1.0, provider: Optional[LLMWaypointProvider] = None):
        super().__init__(grid)
        self.hf = heuristic
        self.weight = weight
        self.provider = provider or LLMWaypointProvider()
        self.targets: List[Tuple[int, int]] = self.provider.get_waypoints(grid)
        # target index
        self.ti = 1 if len(self.targets) > 1 else 0
        self.s_target = self.targets[self.ti]
        # init start h/f
        sx, sy = grid.start
        gx, gy = grid.goal
        h_goal = self.hf(gx - sx, gy - sy)
        h_target = self.hf(self.s_target[0] - sx, self.s_target[1] - sy)
        start = self.open[0]
        start.h = h_goal + h_target
        start.f = start.g + self.weight * start.h
        self.open_map[(sx, sy)] = start

    def _heuristic_two(self, x: int, y: int) -> float:
        gx, gy = self.grid.goal
        tx, ty = self.s_target
        return self.hf(gx - x, gy - y) + self.hf(tx - x, ty - y)

    def _update_target(self):
        if self.ti + 1 < len(self.targets):
            self.ti += 1
            self.s_target = self.targets[self.ti]

    def _reheap_open(self):
        for n in self.open:
            x, y = n.x, n.y
            n.h = self._heuristic_two(x, y)
            n.f = n.g + self.weight * n.h
        heapq.heapify(self.open)

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
            snap["llm_targets"] = self.targets
            return snap
        neighbors: List[Tuple[int, int]] = []
        for nx, ny in self.grid.neighbors(cur.x, cur.y):
            if (nx, ny) in self.closed:
                continue
            tentative_g = cur.g + self.grid.move_cost((cur.x, cur.y), (nx, ny))
            node = self.open_map.get((nx, ny))
            h = self._heuristic_two(nx, ny)
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
            if (nx, ny) == self.s_target and self.s_target != self.grid.goal:
                self._update_target()
                self._reheap_open()
        snap = self.snapshot((cur.x, cur.y), neighbors)
        snap["llm_target"] = self.s_target
        return snap
