import pygame

from pygame import draw, Surface
from .utils import *
from .controller.mark_utils import *

SCREEN_BACKGROUND_COLOR = "black"
GAME_OBJECT_COLOR = "white"
GRID_LINE_WIDTH = 1
LINE_WIDTH = 2
CIRCLE_RADIUS = 60

class TicTacToeView:
    def render(self):
        raise NotImplemented

class ShowNothingTicTacToeView:
    def render(self):
        pass

class ScreenTicTacToeView(TicTacToeView):
    def __init__(self, size, mark_utils: MarkUtils, screen: Surface = None):
        self._screen = screen or pygame.display.set_mode(size)
        self._mark_utils = mark_utils

    def __getattr__(self, name):
        if not name.startswith("draw_"):
            raise AttributeError(f"{type(self).__name__} has no attribute '{name}'")
        name = name[5:]
        function = getattr(draw, name)
        return lambda *args, **kwargs: function(self._screen, *args, **kwargs)

    def render(self, cell_width_size, cell_height_size, dim, marks):
        self._screen.fill(SCREEN_BACKGROUND_COLOR)
        self.render_grid(cell_width_size, cell_height_size, dim)
        for mark in marks:
            self.render_mark(mark)

    def render_grid(self, cell_width_size, cell_height_size, dim):
        for d in range(1, dim):
            x = d * cell_width_size
            y = d * cell_height_size
            self.draw_line(GAME_OBJECT_COLOR, (x, 0), (x, self._screen.get_height()), width=GRID_LINE_WIDTH)
            self.draw_line(GAME_OBJECT_COLOR, (0, y), (self._screen.get_width(), y), width=GRID_LINE_WIDTH)

    def render_mark(self, mark: MarkView):
        assert mark.symbol in self._mark_utils.symbols.values(), f"Error! Passed a mark with a not valid ({mark.symbol})."
        if mark.is_nought:
            self._render_nought(mark)
        else:
            self._render_cross(mark)

    def _render_nought(self, mark: MarkView):
        self.draw_circle(GAME_OBJECT_COLOR, (mark.position), radius=CIRCLE_RADIUS, width=LINE_WIDTH)

    def _render_cross(self, mark: MarkView):
        (x, y) = mark.position
        self._draw_line(x, y, inverted=False)
        self._draw_line(x, y, inverted=True)

    def _draw_line(self, x, y, inverted: bool):
        point_plus_minus = 50
        if not inverted:
            line_points = [(x-point_plus_minus, y-point_plus_minus), (x+point_plus_minus, y+point_plus_minus)]
        else:
            line_points = [(x-point_plus_minus, y+point_plus_minus), (x+point_plus_minus, y-point_plus_minus)] 
        self.draw_lines(GAME_OBJECT_COLOR, closed=True, points=line_points, width=LINE_WIDTH)
