from dataclasses import dataclass
from ..utils import Settings
from typing import List

@dataclass
class Cell:
    """Represent a cell in a :class:`Grid`.

    :param x: Horizontal coordinate of the cell.
    :param y: Vertical coordinate of the cell.
    """

    x: int
    y: int

    def __hash__(self):
        return hash((self.x, self.y))

class Grid:
    """Represent the square grid, composed by cells.

    :param dim: Number of rows and columns in the grid.
    """

    dim: int
    cells: List[Cell]

    def __init__(self, dim: int=Settings.dim):
        self.dim = dim
        self.cells = list(Cell(i, j) for i in range(self.dim) for j in range(self.dim))

    def __eq__(self, other: 'Grid'):
        return self.dim == other.dim and self.cells.__eq__(other.cells)
