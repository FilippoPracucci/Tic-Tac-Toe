from typing import Any, Iterable, List
from pygame.event import Event
import pygame
from tic_tac_toe.log import logger
from tic_tac_toe import TicTacToeGame
from tic_tac_toe.remote import *
from tic_tac_toe.remote.centralised.utils import CoordinationMessageType
from tic_tac_toe.utils import Settings
from tic_tac_toe.model import TicTacToe
from tic_tac_toe.model.game_object import Symbol
from tic_tac_toe.controller import LobbyEvent, ControlEvent
from tic_tac_toe.remote.tcp import TcpConnection, TcpServer, Address
from tic_tac_toe.remote.presentation import serialize, deserialize
import threading, os

class TicTacToeCoordinator(TicTacToeGame):
    """Coordinator game server between two remote players.

    :param game_id: The game identifier.
    :param settings: The optional :class:`Settings`.
    """

    def __init__(self, game_id: int, settings: Settings = None):
        settings = settings or Settings()
        self.logger = logger(f"Coordinator {game_id}")
        super().__init__(settings)
        self.game_id = game_id
        self.server = TcpServer(Address.any_local_port().port, self._on_new_connection)
        self._peers: set[Address] = set()
        self._lock = threading.RLock()

    def create_view(coordinator: 'TicTacToeCoordinator'):
        from tic_tac_toe.view import ShowNothingTicTacToeView
        from tic_tac_toe.controller.local import ControlEvent

        class SendToPeersTicTacToeView(ShowNothingTicTacToeView):
            def render(self) -> None:
                event = coordinator.controller.create_event(ControlEvent.TIME_ELAPSED, dt=coordinator.dt, status=self._tic_tac_toe)
                coordinator._broadcast_to_all_peers(event)

        return SendToPeersTicTacToeView(coordinator.tic_tac_toe)

    def create_controller(coordinator: 'TicTacToeCoordinator'):
        from tic_tac_toe.controller.local import TicTacToeEventHandler, InputHandler

        class Controller(TicTacToeEventHandler, InputHandler):
            def __init__(self, tic_tac_toe: TicTacToe):
                TicTacToeEventHandler.__init__(self, tic_tac_toe)

            def on_player_join(self, tic_tac_toe: TicTacToe, symbol: Symbol, **kwargs) -> None:
                try:
                    super().on_player_join(tic_tac_toe, symbol=symbol)
                except ValueError as exception:
                    if CoordinationMessageType.CONNECTION.value in kwargs:
                        connection: TcpConnection = kwargs[CoordinationMessageType.CONNECTION.value]
                        connection.send(serialize({"error": str(exception)}))

            def on_player_leave(self, tic_tac_toe: TicTacToe, symbol: Symbol) -> None:
                self.on_game_over(tic_tac_toe)

            def on_game_over(self, tic_tac_toe: TicTacToe, **kwargs) -> None:
                super().on_game_over(tic_tac_toe, **kwargs)
                self.post_event(LobbyEvent.DELETE_GAME, game_id=coordinator.game_id)
                coordinator.stop()

            def handle_inputs(self, dt: float = None) -> None:
                self.time_elapsed(dt)

            def handle_events(self) -> None:
                game_over_events: List[Event] = pygame.event.get(ControlEvent.GAME_OVER.value)
                if game_over_events:
                    event = game_over_events.pop()
                    coordinator._broadcast_to_all_peers(event)
                    self.on_game_over(tic_tac_toe=self._tic_tac_toe, **event.dict)
                super().handle_events()

        return Controller(coordinator.tic_tac_toe)

    def at_each_run(self) -> None:
        pass

    def after_run(self) -> None:
        super().after_run()
        self.server.close()

    @property
    def peers(self) -> Set[Address]:
        """Get all the connected peer addresses.

        :return: The set of peer network :class:`Address`.
        """
        with self._lock:
            return set(self._peers)

    @peers.setter
    def peers(self, value: Iterable[Address]) -> None:
        """Replace the collection of connected peers with a new one.

        :param value: The new collection of peer :class:`Address`.
        """
        with self._lock:
            self._peers = set(value)

    def add_peer(self, peer: Address) -> None:
        """Add a new peer address.

        :param peer: The network :class:`Address` of the peer to add.
        """
        with self._lock:
            self._peers.add(peer)

    def remove_peer(self, peer: Address) -> None:
        """Remove a peer address.

        :param peer: The network :class:`Address` of the peer to remove.
        """
        with self._lock:
            if self._peers.__contains__(peer):
                self._peers.remove(peer)

    def _broadcast_to_all_peers(self, message: Any) -> None:
        event = serialize(message)
        for peer in self.peers:
            self.server.connections[peer].send(event)

    def _on_new_connection(self, event: ServerEvent, connection: TcpConnection, address: Address, error: Exception) -> None:
        match event:
            case ServerEvent.LISTEN:
                self.logger.debug(f"Server listening on port {address.port} at {address.ip}")
            case ServerEvent.CONNECT:
                self.logger.debug(f"Open ingoing connection from: {address}")
                self.add_peer(address)
                connection.callback = self._on_message_received
            case ServerEvent.STOP:
                self.logger.debug(f"Stop listening for new connections")
            case ServerEvent.ERROR:
                self.logger.debug(error)

    def _on_message_received(self, event: ConnectionEvent, payload: str, connection: TcpConnection, error: Exception) -> None:
        match event:
            case ConnectionEvent.MESSAGE:
                if payload:
                    self.__handle_message(deserialize(payload), connection=connection)
            case ConnectionEvent.CLOSE:
                self.logger.debug(f"Connection with peer {connection.remote_address} closed")
                self.remove_peer((connection.remote_address.host, connection.remote_address.port))
                self.controller.post_event(ControlEvent.GAME_OVER)
                self.tic_tac_toe.players.clear()
            case ConnectionEvent.ERROR:
                self.logger.debug(error)
                self.remove_peer((connection.remote_address.host, connection.remote_address.port))

    def __handle_message(self, message: Any, **kwargs) -> None:
        if isinstance(message, pygame.event.Event):
            if ControlEvent.PLAYER_JOIN.matches(message):
                if CoordinationMessageType.CONNECTION.value in kwargs:
                    message.connection = kwargs[CoordinationMessageType.CONNECTION.value]
            elif ControlEvent.PLAYER_LEAVE.matches(message):
                self._broadcast_to_all_peers(message)
            pygame.event.post(message)
        elif isinstance(message, str):
            self._broadcast_to_all_peers(message)
            self.logger.debug(f"Received message: {message}")

def main_coordinator(game_id: int, connection: Connection, settings: Settings = None):
    """Initialize and run the coordinator game server.

    :param game_id: The game identifier.
    :param connection: The pipe :class:`Connection` between the lobby and the game coordinator.
    :param settings: The optional :class:`Settings`.
    """
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    coordinator = TicTacToeCoordinator(game_id, settings)
    connection.send(coordinator.server.address)
    connection.close()
    coordinator.run()
