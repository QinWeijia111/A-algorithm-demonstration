from pydantic import BaseModel
from typing import Tuple, List


class Coord(BaseModel):
    x: int
    y: int


class Snapshot(BaseModel):
    current: Tuple[int, int]
    neighbors: List[Tuple[int, int]]
    open: List[Tuple[Tuple[int, int], float, float, float]]
    closed: List[Tuple[int, int]]
    stats: dict

