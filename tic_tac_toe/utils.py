from dataclasses import dataclass
from typing import Optional
from statistics import mean

@dataclass
class Settings:
    debug: bool = False
    size: tuple = (600, 600)
    fps: int = 60
    host: Optional[str] = None
    port: Optional[int] = None
    gui: bool = True
    dim: int = 3

@dataclass
class Config:
    cell_width_size: int
    cell_height_size: int

    @property
    def cells_area_matrix(self):
        self._cells_area_matrix = dict()
        for i in range(Settings.dim):
            for j in range(Settings.dim):
                self._cells_area_matrix[(i, j)] = ((int(i * self.cell_width_size), int((i + 1) * self.cell_width_size)),
                                        (int(j * self.cell_height_size), int((j + 1) * self.cell_height_size)))
        return self._cells_area_matrix
    
    @property
    def cells_symbol_position(self):
        return {cell: (int(mean(area[0])), int(mean(area[1]))) for cell, area in self.cells_area_matrix.items()}
