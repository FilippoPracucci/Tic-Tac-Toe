from dataclasses import dataclass
from typing import Optional, Tuple, Dict
from statistics import mean

@dataclass
class Settings:
    """Application settings for the game and its interface.

    :param debug: Enable debugging mode.
    :param size: Window size in pixels as a `(width, height)` tuple.
    :param fps: Target frame rate.
    :param host: Host address used in remote mode.
    :param port: Port used for network communication in remote mode.
    :param gui: Whether the GUI should be enabled.
    :param dim: Tic-tac-toe square grid dimension.
    :param lobby_size: Number of players to complete a lobby.
    """

    debug: bool = True
    size: Tuple = (900, 600)
    fps: int = 60
    host: Optional[str] = None
    port: Optional[int] = None
    gui: bool = True
    dim: int = 3
    lobby_size: int = 2

@dataclass
class Config:
    """Grid layout configuration.

    :param cell_width_size: Width of each board cell in pixels.
    :param cell_height_size: Height of each board cell in pixels.
    """

    cell_width_size: int
    cell_height_size: int

    @property
    def cells_area_matrix(self) -> Dict:
        """Return the rectangular bounds of each cell in the board.

        :return: A mapping of cell coordinates to their pixel-area ranges.
        """
        self._cells_area_matrix = dict()
        for i in range(Settings.dim):
            for j in range(Settings.dim):
                self._cells_area_matrix[(i, j)] = ((int(i * self.cell_width_size), int((i + 1) * self.cell_width_size)),
                                        (int(j * self.cell_height_size), int((j + 1) * self.cell_height_size)))
        return self._cells_area_matrix

    @property
    def cells_symbol_position(self) -> Dict:
        """Return the center position for each cell in pixel coordinates.

        :return: A mapping of cell coordinates to their center pixel coordinates.
        """
        return {cell: (int(mean(area[0])), int(mean(area[1]))) for cell, area in self.cells_area_matrix.items()}
