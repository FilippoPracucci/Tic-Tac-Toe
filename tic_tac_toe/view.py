import threading, json
from typing import List, Tuple
import pygame
import pygame_menu
from pygame_menu import themes
from pygame_menu.widgets.widget.dropselect import DropSelect
from pygame_menu.widgets.widget.button import Button
from pygame_menu.widgets.widget.frame import Frame
from pygame import Vector2, draw, Surface
from tic_tac_toe.controller import ControlEvent, InputHandler
from tic_tac_toe.model import TicTacToe, Symbol, Mark

SCREEN_BACKGROUND_COLOR = "black"
GAME_OBJECT_COLOR = "white"
GRID_LINE_WIDTH = 1
LINE_WIDTH = 2
CIRCLE_RADIUS = 60

GAME_IDS_FILE = "games.json"

class TicTacToeView:
    def __init__(self, tic_tac_toe: TicTacToe):
        self._tic_tac_toe = tic_tac_toe

    def render(self):
        raise NotImplemented

class ShowNothingTicTacToeView(TicTacToeView):
    def render(self):
        pass

class LobbyMenu(pygame_menu.Menu):
    def __init__(self, size: Tuple, callback=None):
        pygame.init()
        self._lock = threading.RLock()
        self._game_ids:List[str] = ["0"]
        self._id_selected = 0
        self._screen = pygame.display.set_mode(Vector2(size))
        super().__init__("TicTacToe", size[0], size[1], theme=themes.THEME_BLUE)
        self._menubar._backbox = False
        self.set_onclose(callback)
        self._create_button: Button = None
        self._drop_selector: DropSelect = None
        self._join_button: Button = None
        self.__setup()

    def __setup(self):
        self.init_game_ids()
        self._create_button = self.add.button("Create a new game", self._create_game)
        self._drop_selector = self.add.dropselect(
            title="Game id: ",
            items=self._game_ids,
            placeholder="Select a game id",
            onchange=self._change_id_selected
        )
        self._join_button = self.add.button("Join", self._join_a_game)
        frame: Frame = self.add.frame_h(width=self._screen.get_size()[0], height=self._screen.get_size()[1])
        frame.pack([self._drop_selector, self._join_button])
        self.mainloop(self._screen)

    def _change_id_selected(self, selected: Tuple):
        self._id_selected = int(selected[0])

    def _create_game(self):
        InputHandler().post_event(ControlEvent.PLAYER_CREATE_GAME)
        self.close()

    def _join_a_game(self):
        InputHandler().post_event(ControlEvent.PLAYER_JOIN_GAME, game_id=self._id_selected)
        self.close()

    def init_game_ids(self):
        with open(GAME_IDS_FILE, "r") as file:
            try:
                self._game_ids = list(map(lambda id: str(id), json.load(file)))
            except:
                self._game_ids = ["0"]


class ScreenTicTacToeView(TicTacToeView):
    def __init__(self, tic_tac_toe: TicTacToe, title: str, screen: Surface=None):
        super().__init__(tic_tac_toe)
        pygame.display.set_caption(title)
        self._screen = screen or pygame.display.set_mode(tic_tac_toe.size)

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
        for d in range(1, self._tic_tac_toe.grid.dim):
            x = d * self._tic_tac_toe.config.cell_width_size
            y = d * self._tic_tac_toe.config.cell_height_size
            self.draw_line(GAME_OBJECT_COLOR, (x, 0), (x, self._screen.get_height()), width=GRID_LINE_WIDTH)
            self.draw_line(GAME_OBJECT_COLOR, (0, y), (self._screen.get_width(), y), width=GRID_LINE_WIDTH)

    def render_mark(self, mark: Mark):
        assert mark.symbol in Symbol.values(), f"Error! Passed a mark with a not valid ({mark.symbol})."
        self._render_nought(mark) if mark.is_nought else self._render_cross(mark)

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
