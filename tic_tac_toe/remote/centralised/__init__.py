from multiprocessing import Pipe, Pool
from typing import Any, Dict, List
import pygame
from tic_tac_toe.log import logger
from tic_tac_toe.remote import *
from tic_tac_toe.utils import Settings
from tic_tac_toe.model.game_object import Symbol
from tic_tac_toe.controller import LobbyEvent
from tic_tac_toe.remote.tcp import TcpConnection, TcpServer, Address
from tic_tac_toe.remote.presentation import serialize, deserialize
from tic_tac_toe.remote.centralised.utils import CoordinationMessageType, Config
from tic_tac_toe.remote.centralised.coordinator import main_coordinator
import threading, json, os

class LobbyCoordinator():
    """ Coordinates the lobby and manages multiple games.

    :param settings: The optional :class:`Settings`.
    """

    def __init__(self, settings: Settings = None):
        self.logger = logger("LobbyCoordinator")
        self.settings = settings or Settings()
        self.controller = self._create_controller()
        self.server = TcpServer(self.settings.port or Config.DEFAULT_PORT.value, self._on_new_connection)
        self.clock = pygame.time.Clock()
        self.running = True
        self._processes_pool = Pool()
        self._lock = threading.RLock()
        self.__coordinators: Dict[int, Address] = {}
        self.__joinable_games: Dict[int, str] = {}
        self.__joinable_games_subscribers: Dict[Address, TcpConnection] = {}
        open(Config.JOINABLE_GAMES_FILE.value, "x")

    @property
    def coordinators(self) -> Dict[int, Address]:
        """Get the active game coordinators.

        :return: The mapping of game IDs to coordinator :class:`Address`.
        """
        with self._lock:
            return self.__coordinators

    @coordinators.setter
    def coordinators(self, coordinators: Dict[int, Address]) -> None:
        """Replace the active game coordinators with a new dictionary.

        :param coordinators: The new mapping of game IDs to coordinator :class:`Address`.
        """
        with self._lock:
            self.__coordinators = coordinators

    def before_run(self) -> None:
        """Initialize pygame before starting the lobby coordinator."""
        pygame.init()

    def after_run(self) -> None:
        """Clean up pygame and remove joinable game IDs store file after coordinator stops."""
        pygame.quit()
        os.remove(Config.JOINABLE_GAMES_FILE.value)

    def run(self) -> None:
        """Start the lobby coordinator event loop."""
        try:
            self.before_run()
            while self.running:
                self.controller.handle_events()
        finally:
            self._processes_pool.terminate()
            self._processes_pool.join()
            self.after_run()

    def stop(self) -> None:
        """Stop the lobby coordinator event loop."""
        self.running = False

    def _create_controller(lobby_coordinator: 'LobbyCoordinator'):
        from tic_tac_toe.controller import LobbyEventHandler

        class Controller(LobbyEventHandler):
            def on_create_game(self, **kwargs) -> None:
                game_id = max(lobby_coordinator._game_ids(), default=0) + 1
                lobby_connection, coordinator_connection = Pipe()
                lobby_coordinator._processes_pool.apply_async(
                    func=main_coordinator,
                    args=(game_id, coordinator_connection, lobby_coordinator.settings),
                    callback=lambda _: self.on_delete_game(game_id)
                )
                coordinator_address = lobby_connection.recv()
                lobby_coordinator._add_coordinator(game_id, coordinator_address)
                if "symbol" in kwargs:
                    lobby_coordinator._add_joinable_game(game_id, str(kwargs["symbol"].opposite.value))
                self.__update_and_broadcast_joinable_games()
                if CoordinationMessageType.CONNECTION.value in kwargs:
                    connection: TcpConnection = kwargs[CoordinationMessageType.CONNECTION.value]
                    connection.send(serialize({CoordinationMessageType.COORDINATOR.value: (connection.local_address.ip, coordinator_address.port)}))

            def on_delete_game(self, game_id: int) -> None:
                lobby_coordinator._remove_coordinator_by_id(game_id)
                lobby_coordinator._remove_joinable_game(game_id)
                self.__update_and_broadcast_joinable_games()

            def on_join_game(self, game_id: int, **kwargs) -> None:
                connection: TcpConnection = kwargs[CoordinationMessageType.CONNECTION.value] if CoordinationMessageType.CONNECTION.value in kwargs else None
                lobby_coordinator._remove_joinable_game(game_id)
                self.__update_and_broadcast_joinable_games()
                if game_id in lobby_coordinator._game_ids():
                    if connection is not None:
                        connection.send(serialize({CoordinationMessageType.COORDINATOR.value: (connection.local_address.ip, lobby_coordinator.coordinators[game_id].port)}))
                else:
                    error = f"Game {game_id} does not exist! Impossible to join."
                    lobby_coordinator.logger.debug(error)
                    if connection is not None:
                        connection.send(serialize({CoordinationMessageType.ERROR.value: error}))

            def on_request_joinable_games(self, **kwargs) -> None:
                lobby_coordinator.logger.debug(f"Request joinable game ids: {kwargs}")
                connection: TcpConnection = kwargs[CoordinationMessageType.CONNECTION.value] if CoordinationMessageType.CONNECTION.value in kwargs else None
                if connection is not None:
                    self.__init_joinable_games()
                    connection.send(serialize({CoordinationMessageType.JOINABLE_GAMES.value: lobby_coordinator._joinable_games()}))
                    lobby_coordinator._add_joinable_games_subscriber(connection)

            def __broadcast_joinable_games(self) -> None:
                for connection in lobby_coordinator._joinable_games_subscribers():
                    try:
                        connection.send(serialize({CoordinationMessageType.JOINABLE_GAMES.value: lobby_coordinator._joinable_games()}))
                    except Exception as e:
                        lobby_coordinator.logger.debug(f"Error while broadcasting game IDs to {connection.remote_address}")

            def __update_games_id_db(self) -> None:
                with open(Config.JOINABLE_GAMES_FILE.value, "w") as file:
                    json.dump(lobby_coordinator._joinable_games(), file)

            def __update_and_broadcast_joinable_games(self) -> None:
                self.__update_games_id_db()
                self.__broadcast_joinable_games()

            def __init_joinable_games(self) -> None:
                with open(Config.JOINABLE_GAMES_FILE.value, "r") as file:
                    try:
                        self.joinable_games = dict(map(lambda k, v: (int(k), str(Symbol(v).opposite.value)), json.load(file)))
                    except:
                        self.joinable_games = []

        return Controller()

    def _game_ids(self) -> List[int]:
        return list(self.coordinators.keys())

    def _joinable_games(self) -> Dict[int, str]:
        return self.__joinable_games

    def _add_joinable_game(self, game_id: int, symbol: str) -> None:
        with self._lock:
            self.__joinable_games[game_id] = symbol

    def _remove_joinable_game(self, game_id: int) -> None:
        with self._lock:
            self.__joinable_games.pop(game_id)

    def _add_coordinator(self, game_id: int, address: Address) -> None:
        with self._lock:
            self.__coordinators.update({game_id: address})

    def _remove_coordinator_by_id(self, game_id: int) -> None:
        with self._lock:
            self.__coordinators.pop(game_id)

    def _add_joinable_games_subscriber(self, connection: TcpConnection) -> None:
        with self._lock:
            self.__joinable_games_subscribers[connection.remote_address] = connection

    def _remove_joinable_games_subscriber_by_address(self, address: Address) -> None:
        with self._lock:
            if address in self.__joinable_games_subscribers:
                self.__joinable_games_subscribers.pop(address)

    def _joinable_games_subscribers(self) -> List[TcpConnection]:
        with self._lock:
            return list(self.__joinable_games_subscribers.values())

    def _on_new_connection(self, event: ServerEvent, connection: TcpConnection, address: Address, error: Exception) -> None:
        match event:
            case ServerEvent.LISTEN:
                self.logger.debug(f"Server listening on port {address.port} at {address.ip}")
            case ServerEvent.CONNECT:
                self.logger.debug(f"Open ingoing connection from: {address}")
                connection.callback = self._on_message_received
            case ServerEvent.STOP:
                self.logger.debug(f"Stop listening for new connections")
            case ServerEvent.ERROR:
                self.logger.debug(error)

    def _on_message_received(self, event: ConnectionEvent, payload: str, connection: TcpConnection, error: Exception) -> None:
        match event:
            case ConnectionEvent.MESSAGE:
                if payload is not None:
                    self.__handle_message(deserialize(payload), connection=connection)
            case ConnectionEvent.CLOSE:
                self.logger.debug(f"Connection with coordinator {connection.remote_address} closed")
                self._remove_joinable_games_subscriber_by_address(connection.remote_address)
            case ConnectionEvent.ERROR:
                self.logger.debug(error)
                self._remove_joinable_games_subscriber_by_address(connection.remote_address)

    def __handle_message(self, message: Any, **kwargs) -> None:
        if any(e.matches(message) for e in (
            LobbyEvent.CREATE_GAME,
            LobbyEvent.JOIN_GAME,
            LobbyEvent.REQUEST_JOINABLE_GAMES
        )) and (CoordinationMessageType.CONNECTION.value in kwargs):
            message.connection = kwargs[CoordinationMessageType.CONNECTION.value]
        pygame.event.post(message)

def main_lobby(settings: Settings=None):
    """Initialize and run the lobby coordinator server.

    :param settings: The optional :class:`Settings`.
    """

    os.environ["SDL_VIDEODRIVER"] = "dummy"
    LobbyCoordinator(settings).run()
