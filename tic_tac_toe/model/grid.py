from dataclasses import dataclass
from ..utils import Settings

@dataclass
class Cell:
    x: int
    y: int

class Grid:
    dim: int
    cells: list[Cell]

    def __init__(self, dim = Settings.dim):
        self.dim = dim
        self.cells = list(Cell(i, j) for i in range(self.dim) for j in range(self.dim))
