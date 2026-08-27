import pygame
from pygame import draw, Surface
from tic_tac_toe.model import TicTacToe, Symbol, Mark

SCREEN_BACKGROUND_COLOR = "black"
GAME_OBJECT_COLOR = "white"
GRID_LINE_WIDTH = 1
LINE_WIDTH = 2
CIRCLE_RADIUS = 60

class TicTacToeView:
    """Base class for a tic-tac-toe game view.

    :param tic_tac_toe: The :class:`TicTacToe` instance to display.
    """

    def __init__(self, tic_tac_toe: TicTacToe):
        self._tic_tac_toe = tic_tac_toe

    def render(self):
        """Render the current game state."""
        raise NotImplemented

class ShowNothingTicTacToeView(TicTacToeView):
    """:class:`TicTacToeView` that does not render anything."""

    def render(self):
        pass

class ScreenTicTacToeView(TicTacToeView):
    """Render the game on a pygame window.

    :param tic_tac_toe: The :class:`TicTacToe` instance to display.
    :param title: The title shown in the window caption.
    :param screen: The optional pygame surface to draw on.
    """

    def __init__(self, tic_tac_toe: TicTacToe, title: str, screen: Surface=None):
        super().__init__(tic_tac_toe)
        self._title = title
        pygame.display.set_caption(title)
        self._screen = screen or pygame.display.set_mode(tic_tac_toe.size)

    @property
    def title(self) -> str:
        """Return the window title string.

        :return: The window title.
        """
        return self._title

    @title.setter
    def title(self, value: str):
        """Set the window title.

        :param value: The new title of the window.
        """
        self._title = value
        pygame.display.set_caption(self._title)

    def __getattr__(self, name: str):
        if not name.startswith("draw_"):
            raise AttributeError(f"{type(self).__name__} has no attribute '{name}'")
        name = name[5:]
        function = getattr(draw, name)
        return lambda *args, **kwargs: function(self._screen, *args, **kwargs)

    def render(self):
        self._screen.fill(SCREEN_BACKGROUND_COLOR)
        self.render_grid()
        for mark in self._tic_tac_toe.marks:
            self.render_mark(mark)

    def render_grid(self):
        """Render the grid on the screen."""
        for d in range(1, self._tic_tac_toe.grid.dim):
            x = d * self._tic_tac_toe.config.cell_width_size
            y = d * self._tic_tac_toe.config.cell_height_size
            self.draw_line(GAME_OBJECT_COLOR, (x, 0), (x, self._screen.get_height()), width=GRID_LINE_WIDTH)
            self.draw_line(GAME_OBJECT_COLOR, (0, y), (self._screen.get_width(), y), width=GRID_LINE_WIDTH)

    def render_mark(self, mark: Mark):
        """Render a single mark on the board.

        :param mark: The :class:`Mark` to draw.
        """
        assert mark.symbol in Symbol.values(), f"Error! Passed a mark with a not valid ({mark.symbol})."
        self._render_nought(mark) if mark.symbol.is_nought else self._render_cross(mark)

    def _render_nought(self, mark: Mark):
        self.draw_circle(GAME_OBJECT_COLOR, (mark.position), radius=CIRCLE_RADIUS, width=LINE_WIDTH)

    def _render_cross(self, mark: Mark):
        (x, y) = mark.position
        self._draw_line(x, y, inverted=False)
        self._draw_line(x, y, inverted=True)

    def _draw_line(self, x: float, y: float, inverted: bool):
        point_plus_minus = 50
        if not inverted:
            line_points = [(x-point_plus_minus, y-point_plus_minus), (x+point_plus_minus, y+point_plus_minus)]
        else:
            line_points = [(x-point_plus_minus, y+point_plus_minus), (x+point_plus_minus, y-point_plus_minus)] 
        self.draw_lines(GAME_OBJECT_COLOR, closed=True, points=line_points, width=LINE_WIDTH)
