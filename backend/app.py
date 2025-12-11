from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional, Tuple, Dict, Any
import time

from .algorithms.grid import Grid
from .algorithms.astar import AStar, Heuristic
from .algorithms.dijkstra import Dijkstra
from .algorithms.greedy import GreedyBestFirst
from .algorithms.llm_astar import LLMAStar as LLMAStarAlgo

app = FastAPI()
app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/")
def index():
    return FileResponse("frontend/index.html")


class StartPayload(BaseModel):
    size: int
    obstacles: List[Tuple[int, int]]
    start: Tuple[int, int]
    goal: Tuple[int, int]
    diagonal: bool = True
    algorithm: str = "astar"
    heuristic: str = "octile"
    weight: float = 1.0
    llm_model: str = "deepseek"
    llm_enabled: bool = False


class Runner:
    def __init__(self):
        self.grid: Optional[Grid] = None
        self.algo: Optional[Any] = None
        self.started_at: float = 0.0
        self.finished: bool = False
        self.last_snapshot: Optional[Dict[str, Any]] = None

    def start(self, payload: StartPayload):
        self.grid = Grid(payload.size, set(map(tuple, payload.obstacles)), tuple(payload.start), tuple(payload.goal), payload.diagonal)
        import os
        llm_flag = payload.llm_enabled or os.getenv("LLM_GUIDE", "0") in ("1", "true", "True")
        if payload.algorithm == "astar":
            h = getattr(Heuristic, payload.heuristic, Heuristic.octile)
            if llm_flag:
                self.algo = LLMAStarAlgo(self.grid, heuristic=h, weight=payload.weight)
            else:
                self.algo = AStar(self.grid, heuristic=h, weight=payload.weight)
        elif payload.algorithm == "dijkstra":
            self.algo = Dijkstra(self.grid)
        elif payload.algorithm == "greedy":
            h = getattr(Heuristic, payload.heuristic, Heuristic.octile)
            self.algo = GreedyBestFirst(self.grid, heuristic=h)
        elif payload.algorithm == "llm_astar":
            h = getattr(Heuristic, payload.heuristic, Heuristic.octile)
            self.algo = LLMAStarAlgo(self.grid, heuristic=h, weight=payload.weight)
        else:
            self.algo = AStar(self.grid, heuristic=Heuristic.octile)
        self.finished = False
        self.started_at = time.time()
        self.last_snapshot = None

    def step(self) -> Dict[str, Any]:
        if not self.algo:
            return {"type": "error", "message": "not started"}
        snap = self.algo.step()
        if snap.get("finished"):
            self.finished = True
            snap["stats"]["elapsed_ms"] = int((time.time() - self.started_at) * 1000)
            return {"type": "finished", **snap}
        self.last_snapshot = snap
        return {"type": "snapshot", **snap}


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    runner = Runner()
    try:
        while True:
            data = await ws.receive_json()
            t = data.get("type")
            if t == "start":
                payload = StartPayload(**data.get("payload", {}))
                runner.start(payload)
                await ws.send_json({"type": "ok"})
                try:
                    init_snap = runner.algo.snapshot(tuple(payload.start), [], finished=False)
                    await ws.send_json({"type": "snapshot", **init_snap})
                except Exception:
                    pass
            elif t == "step":
                res = runner.step()
                await ws.send_json(res)
            elif t == "reset":
                runner = Runner()
                await ws.send_json({"type": "ok"})
            else:
                await ws.send_json({"type": "error", "message": "unknown command"})
    except WebSocketDisconnect:
        return
