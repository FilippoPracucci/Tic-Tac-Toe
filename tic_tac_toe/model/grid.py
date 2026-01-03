from dataclasses import dataclass
from ..utils import Settings
from typing import List

@dataclass
class Cell:
    x: int
    y: int

    def __hash__(self):
        return hash((self.x, self.y))

class Grid:
    dim: int
    cells: List[Cell]

    def __init__(self, dim : Settings=Settings.dim):
        self.dim = dim
        self.cells = list(Cell(i, j) for i in range(self.dim) for j in range(self.dim))

    def __eq__(self, other: 'Grid'):
        return self.dim == other.dim and self.cells.__eq__(other.cells)
