from ..log import logger
from enum import Enum
from dataclasses import dataclass
from .game_object import *

class Symbol(Enum):
    NOUGHT = "O"
    CROSS = "X"

    @property
    def is_nought(self) -> bool:
        return self.value == "O"

    @property
    def is_cross(self) -> bool:
        return self.value == "X"

    @classmethod
    def values(cls) -> list['Symbol']:
        return list(cls.__members__.values())

@dataclass
class Cell:
    x: int
    y: int

class Mark(GameObject):
    cell: Cell
    symbol: Symbol

    def __init__(self, cell: Cell, symbol: Symbol, size=None, position=None, name=None):
        super().__init__(size, position, name or "mark_" + symbol.name)
        self.cell = cell
        self.symbol = symbol

@dataclass
class Config:
    dim: int
    cell_width_size: int
    cell_height_size: int

    @property
    def cells_area_matrix(self) -> dict:
        cells_matrix = dict()
        for i in range(self.dim):
            for j in range(self.dim):
                cells_matrix[(i, j)] = ((int(i * self.cell_width_size), int((i + 1) * self.cell_width_size)),
                                        (int(j * self.cell_height_size), int((j + 1) * self.cell_height_size)))
        return cells_matrix

class Grid:
    dim: int
    cells: list[Cell]

    def __init__(self, dim):
        self.dim = dim
        self.cells = list(Cell(i, j) for i in range(self.dim) for j in range(self.dim))