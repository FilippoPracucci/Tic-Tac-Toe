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
from pygame import Vector2
from tic_tac_toe.model import Symbol

class LobbyMenu(pygame_menu.Menu):
    """Lobby menu used to create or join a game.

    :param size: The size of the menu window in pixels as a `(width, height)` tuple.
    """

    def __init__(self, size: Tuple):
        pygame.init()
        self._lock = threading.RLock()
        self._joinable_games: Dict[int, str] = {}
        self._updates_queue: Queue = None
        self._symbol_selected: Symbol = Symbol.CROSS
        self._id_selected: Optional[int] = None
        self._screen = pygame.display.set_mode(Vector2(size))
        super().__init__("TicTacToe", size[0], size[1], theme=themes.THEME_BLUE, overflow=False)
        self._join_frame: Frame = None
        self._menubar._backbox = False
        self._callback_on_create_game: callable = None
        self._callback_on_join_game: callable = None
        self._symbol_selector: DropSelect = None
        self._game_selector: DropSelect = None
        self._join_button: Button = None
        self._no_games_label: Label = None
        self._message_label: Label = None

    def start(
        self,
        callback_on_create_game: callable,
        callback_on_join_game: callable,
        joinable_games: Dict[int, str]={},
        updates_queue: Queue=None,
        message_to_show: str=None
    ):
        """Open the lobby menu and setup its callbacks.

        :param callback_on_create_game: The function called when creating a new game.
        :param callback_on_join_game: The function called when joining an existing game.
        :param joinable_games: The mapping of game ids to symbol available for joining.
        :param updates_queue: The queue used to refresh the available games.
        :param message_to_show: The optional message displayed in the lobby.
        """
        self._joinable_games = joinable_games
        self._updates_queue = updates_queue
        self._callback_on_create_game = callback_on_create_game
        self._callback_on_join_game = callback_on_join_game
        if message_to_show is not None:
            self._message_label = self.add.label(f"Last game message: {message_to_show}", font_color="black", max_char=-1)
        self.__setup()
        self.mainloop(self._screen, bgfun=self._poll_updates if self._updates_queue else None)

    def stop(self):
        """Disable the menu if it is currently enabled."""
        with self._lock:
            if not self.is_enabled():
                return
            try:
                self.disable()
            except RuntimeError:
                pass

    def __setup(self):
        self.enable()
        self.center_content()
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
