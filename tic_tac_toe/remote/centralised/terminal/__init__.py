from datetime import datetime
from queue import Queue
from typing import Any, Dict
from pygame.event import Event
import pygame
from tic_tac_toe.log import logger
from tic_tac_toe import TicTacToeGame
from tic_tac_toe.remote import *
from tic_tac_toe.utils import Settings
from tic_tac_toe.model import TicTacToe
from tic_tac_toe.model.game_object import Symbol
from tic_tac_toe.controller import LobbyEvent, ControlEvent
from tic_tac_toe.remote.tcp import TcpClient, Address
from tic_tac_toe.remote.presentation import serialize, deserialize
from tic_tac_toe.view.lobby_menu import LobbyMenu
from tic_tac_toe.remote.centralised.utils import CoordinationMessageType, Config
import threading

class TicTacToeTerminal(TicTacToeGame):
    """Terminal game client connecting to a lobby coordinator to create or join a game.
    Then connects to the game coordinator to play the game with another player.
    """

    def __init__(self, settings: Settings = None, lobby_menu: LobbyMenu = None, message_to_show: str = None):
        settings = settings or Settings()
        self.symbol: Symbol = None
        self.connected_to_coordinator: bool = False
        self.joinable_game_ids: Dict[int, str] = {}
        self.joinable_games_updates: Queue[Dict[int, str]] = Queue()
        self._lobby_menu: LobbyMenu = lobby_menu
        self._message_to_show: str = message_to_show
        super().__init__(settings)
        self.logger = logger("Terminal")
        self.client = TcpClient(Address(host=self.settings.host or Config.DEFAULT_HOST.value, port=self.settings.port or Config.DEFAULT_PORT.value))
        self._lock = threading.RLock()
        self._thread_receiver = threading.Thread(target=self._handle_ingoing_messages, daemon=True)
        self._thread_receiver.start()
        self._thread_sender = threading.Thread(target=self._send_message, daemon=True)
        self._thread_sender.start()
        self.controller.post_event(LobbyEvent.REQUEST_JOINABLE_GAME_IDS)

    def wait_for_game_ids(self, timeout: float = None) -> Dict[int, str]:
        """Wait for updated list of joinable game IDs from the lobby.

        :param timeout: The maximum time to wait in seconds.
        :return: The mapping of game IDs to required opponent symbol string.
        """
        try:
            ids = self.joinable_games_updates.get(timeout=timeout)
            self.joinable_game_ids = ids
            return ids
        except Exception as e:
            self.logger.error(f"Error while waiting for game IDs: {e}")

    def create_controller(terminal: 'TicTacToeTerminal'):
        from tic_tac_toe.controller.local import TicTacToeInputHandler, EventHandler

        class Controller(TicTacToeInputHandler, EventHandler):
            def __init__(self, tic_tac_toe: TicTacToe):
                TicTacToeInputHandler.__init__(self, tic_tac_toe)

            def mouse_clicked(self) -> None:
                if terminal.tic_tac_toe.is_player_lobby_full():
                    pos = self._command.click().__getattribute__("click_point")
                    self.post_event(ControlEvent.MARK_PLACED, cell=self._to_cell(pos), symbol=terminal.symbol)

            def post_event(self, event: Event | LobbyEvent | ControlEvent, **kwargs) -> Event:
                pygame_event = super().post_event(event, **kwargs)
                if isinstance(event, LobbyEvent) \
                    or (terminal.connected_to_coordinator and not ControlEvent.TIME_ELAPSED.matches(pygame_event)):
                    terminal.logger.debug(f"Send event {pygame_event}")
                    terminal.client.send(serialize(pygame_event))
                return pygame_event

            def handle_inputs(self, dt: float = None) -> None:
                if terminal.connected_to_coordinator:
                    return super().handle_inputs(dt, terminal.symbol)
                else:
                    for event in pygame.event.get(pygame.KEYDOWN):
                        if event.key == pygame.K_ESCAPE:
                            self.post_event(ControlEvent.PLAYER_LEAVE, symbol=terminal.symbol)
                    pygame.event.clear(self.INPUT_EVENTS)

            def on_player_create_game(self, symbol: Symbol) -> None:
                terminal.logger.debug(f"Requesting game creation from lobby")
                terminal.symbol = symbol
                terminal.view.title = f"Player {symbol.value}"
                self.post_event(LobbyEvent.CREATE_GAME, symbol=symbol)

            def on_player_join_game(self, symbol: Symbol, game_id: int) -> None:
                terminal.logger.debug(f"Requesting join game {game_id} from lobby")
                terminal.symbol = symbol
                terminal.view.title = f"Player {symbol.value}"
                self.post_event(LobbyEvent.JOIN_GAME, game_id=game_id, symbol=symbol)

            def on_change_turn(self, tic_tac_toe: TicTacToe) -> None:
                tic_tac_toe.change_turn()
                tic_tac_toe.remove_random_mark()

            def on_time_elapsed(self, tic_tac_toe: TicTacToe, dt: float, status: TicTacToe = None) -> None: # type: ignore[override]
                if not status:
                    tic_tac_toe.update(dt)
                else:
                    tic_tac_toe.override(status)

            def on_player_leave(self, tic_tac_toe: TicTacToe, symbol: Symbol) -> None:
                if symbol != terminal.symbol:
                    terminal._message_to_show = f"You won because other player left the game!"
                elif tic_tac_toe.is_player_lobby_full():
                    terminal._message_to_show = f"You lost because you left the game!"
                if terminal._message_to_show is not None:
                    print(terminal._message_to_show)
                terminal.restart()

            def on_game_over(self, tic_tac_toe: TicTacToe, **kwargs) -> None:
                if "symbol" in kwargs:
                    terminal._message_to_show = f"You won!" if kwargs["symbol"] == terminal.symbol else f"You lost!"
                    print(terminal._message_to_show)
                    terminal.restart()
                else:
                    print(f"Game ended: Other player disconnected")
                    terminal.restart()

        return Controller(terminal.tic_tac_toe)

    def _handle_ingoing_messages(self) -> None:
        while self.running:
            try:
                message = self.client.receive()
                if message is not None:
                    self.__handle_message(deserialize(message))
            except ConnectionResetError:
                if self.running:
                    pygame.event.post(pygame.event.Event(LobbyEvent.COORDINATOR_STOPPED.value))
                    print(f"Game ended: coordinator stopped")
                    self.stop()
                break

    def __handle_message(self, message: Any) -> None:
        if isinstance(message, pygame.event.Event):
            pygame.event.post(message)
        elif isinstance(message, dict):
            self.__handle_dict_message(message)
        elif isinstance(message, str):
            print(message)

    def __handle_dict_message(self, message: Dict) -> None:
        if CoordinationMessageType.ERROR.value in message:
            self.logger.debug(message[CoordinationMessageType.ERROR.value])
            self.stop()
        elif CoordinationMessageType.GAME_IDS.value in message:
            self.joinable_game_ids = message[CoordinationMessageType.GAME_IDS.value]
            self.joinable_games_updates.put(self.joinable_game_ids)
        elif CoordinationMessageType.COORDINATOR.value in message:
            coord_address = Address(message[CoordinationMessageType.COORDINATOR.value][0], message[CoordinationMessageType.COORDINATOR.value][1])
            self.logger.debug(f"Received coordinator address {coord_address}")
            with self._lock:
                old_client = self.client
                old_client.close()
                self.client = TcpClient(coord_address)
                self.connected_to_coordinator = True
            self.controller.post_event(ControlEvent.PLAYER_JOIN, symbol=self.symbol)

    def _callback_on_create_game(self, selected_symbol: Symbol) -> None:
        """Game creation callback from lobby menu.

        :param selected_symbol: The :class:`Symbol` selected by the player creating the game.
        """
        self.controller.post_event(ControlEvent.PLAYER_CREATE_GAME, symbol=selected_symbol)
        self._lobby_menu = None

    def _callback_on_join_game(self, selected_symbol: Symbol, selected_game_id: int) -> None:
        """Game join callback from lobby menu.

        :param selected_symbol: The :class:`Symbol` selected by the player joining the game.
        :param selected_game_id: The game to join identifier.
        """
        self.controller.post_event(ControlEvent.PLAYER_JOIN_GAME, symbol=selected_symbol, game_id=selected_game_id)
        self._lobby_menu = None

    def before_run(self) -> None:
        super().before_run()
        if self._lobby_menu is not None:
            self.wait_for_game_ids(timeout=5)
            self._lobby_menu.start(
                callback_on_create_game=self._callback_on_create_game,
                callback_on_join_game=self._callback_on_join_game,
                joinable_games=self.joinable_game_ids,
                updates_queue=self.joinable_games_updates,
                message_to_show=self._message_to_show
            )

    def after_run(self) -> None:
        super().after_run()
        self.client.close()

    def _send_message(self) -> None:
        while self.running:
            try:
                msg = input()
                self.logger.debug(f"Send {msg} to the opponent")
                if msg is not None:
                    self.client.send(serialize(self.message(msg, f"Player '{self.symbol.value}'")))
            except (EOFError, KeyboardInterrupt):
                self.logger.debug("Error while sending the message")

    def message(self, text: str, sender: str, timestamp: datetime = None) -> str:
        """Format a chat message with timestamp and sender information.

        :param text: The message content.
        :param sender: The name of the message sender.
        :param timestamp: The timestamp of the message (uses current time if None).
        :return: The formatted message string.
        """
        if timestamp is None:
            timestamp = datetime.now()
        return f"[{timestamp.isoformat(timespec='minutes')}] {sender}: {text.strip()}"

    def restart(self) -> None:
        """Stop the current game and restart a new session."""
        self.stop()
        main_terminal(self.settings, message_to_show=self._message_to_show)

def main_terminal(settings: Settings = None, message_to_show: str = None):
    """Initialize and run the terminal game client.

    :param settings: The optional :class:`Settings`.
    :param message_to_show: The optional message to display in the lobby menu.
    """
    lobby_menu = LobbyMenu(size=settings.size)
    TicTacToeTerminal(settings, lobby_menu, message_to_show=message_to_show).run()
