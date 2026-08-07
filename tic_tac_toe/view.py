from queue import Queue, Empty
import threading
from typing import Dict, Optional, Tuple
import pygame
import pygame_menu
from pygame_menu import themes
from pygame_menu.widgets.widget.dropselect import DropSelect
from pygame_menu.widgets.widget.button import Button
from pygame_menu.widgets.widget.frame import Frame
from pygame_menu.widgets.widget.label import Label
from pygame import Vector2, draw, Surface
from tic_tac_toe.controller import ControlEvent, InputHandler
from tic_tac_toe.model import TicTacToe, Symbol, Mark

SCREEN_BACKGROUND_COLOR = "black"
GAME_OBJECT_COLOR = "white"
GRID_LINE_WIDTH = 1
LINE_WIDTH = 2
CIRCLE_RADIUS = 60

class TicTacToeView:
    def __init__(self, tic_tac_toe: TicTacToe):
        self._tic_tac_toe = tic_tac_toe

    def render(self):
        raise NotImplemented

class ShowNothingTicTacToeView(TicTacToeView):
    def render(self):
        pass

class LobbyMenu(pygame_menu.Menu):
    def __init__(self, size: Tuple):
        pygame.init()
        self._lock = threading.RLock()
        self._joinable_games: Dict[int, str] = {}
        self._updates_queue: Queue = None
        self._symbol_selected: Symbol = Symbol.CROSS
        self._id_selected: Optional[int] = None
        self._screen = pygame.display.set_mode(Vector2(size))
        super().__init__("TicTacToe", size[0], size[1], theme=themes.THEME_BLUE)
        self._join_frame: Frame = None
        self._menubar._backbox = False
        self._callback_on_create_game: callable = None
        self._callback_on_join_game: callable = None
        self._symbol_selector: DropSelect = None
        self._game_selector: DropSelect = None
        self._join_button: Button = None
        self._no_games_label: Label = None

    def start(
        self,
        callback_on_create_game: callable,
        callback_on_join_game: callable,
        joinable_games: Dict[int, str]={},
        updates_queue: Queue=None
    ):
        self._joinable_games = joinable_games
        self._updates_queue = updates_queue
        self._callback_on_create_game = callback_on_create_game
        self._callback_on_join_game = callback_on_join_game
        self.enable()
        self.__setup()
        self.mainloop(self._screen, bgfun=self._poll_updates if self._updates_queue else None)

    def stop(self):
        self.close()
        self.disable()

    def __setup(self):
        self._symbol_selector = self.add.dropselect(
            title="Symbol: ",
            items=list(map(lambda s: str(s.value), Symbol.values())),
            placeholder="Select a symbol",
            onchange=self._change_symbol_selected
        )
        self.add.button("Create a new game", action=self._create_game)
        self._join_frame = self.add.frame_h(width=self._screen.get_size()[0], height=self._screen.get_size()[1])
        self._populate_join_section()

    def _poll_updates(self):
        try:
            new_joinable_games = self._updates_queue.get_nowait()
        except Empty:
            return
        if new_joinable_games != self._joinable_games:
            self._refresh_menu(new_joinable_games)

    def _refresh_menu(self, new_joinable_games: Dict[int, str]):
        self._joinable_games = new_joinable_games
        self._id_selected = None
        for widget in (self._game_selector, self._join_button, self._no_games_label):
            if widget is not None:
                try:
                    self._join_frame.unpack(widget)
                except ValueError:
                    pass
                self.remove_widget(widget)
        self._game_selector = None
        self._join_button = None
        self._no_games_label = None
        self._populate_join_section()
        self._join_frame.force_menu_surface_update()

    def _populate_join_section(self):
        if self._joinable_games:
            self._game_selector = self.add.dropselect(
                title="Game id: ",
                items=list(map(str, self._joinable_games.keys())),
                placeholder="Select a game id",
                onchange=self._change_id_selected_and_update
            )
            self._join_button = self.add.button("Join", self._join_a_game)
            self._join_frame.pack([self._game_selector, self._join_button])
        else:
            self._no_games_label = self.add.label("No games available to join.")
            self._join_frame.pack(self._no_games_label)

    def _change_id_selected_and_update(self, selected: Tuple):
        self._id_selected = int(selected[0])
        self._symbol_selector.update_items([self._joinable_games[str(self._id_selected)]])

    def _change_symbol_selected(self, selected: Tuple):
        self._symbol_selected = Symbol(selected[0])

    def _create_game(self):
        self._callback_on_create_game(self._symbol_selected)
        self.stop()

    def _join_a_game(self):
        self._callback_on_join_game(self._symbol_selected, self._id_selected)
        self.stop()


class ScreenTicTacToeView(TicTacToeView):
    def __init__(self, tic_tac_toe: TicTacToe, title: str, screen: Surface=None):
        super().__init__(tic_tac_toe)
        self._title = title
        pygame.display.set_caption(title)
        self._screen = screen or pygame.display.set_mode(tic_tac_toe.size)

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, value: str):
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
