from datetime import datetime
from multiprocessing import Process, Pipe
from typing import Any, Dict, Iterable, List, Optional
from pygame.event import Event
import pygame
from tic_tac_toe.log import logger
from tic_tac_toe import TicTacToeGame
from tic_tac_toe.remote import *
from tic_tac_toe.utils import Settings
from tic_tac_toe.model import TicTacToe
from tic_tac_toe.model.game_object import Symbol
from tic_tac_toe.controller import LobbyEvent, ControlEvent
from tic_tac_toe.remote.tcp import TcpClient, TcpConnection, TcpServer, Address
from tic_tac_toe.remote.presentation import serialize, deserialize
import threading


DEFAULT_HOST = "localhost"
DEFAULT_PORT = 12345


class LobbyCoordinator():

    def __init__(self, settings: Settings=None):
        self.logger = logger("LobbyCoordinator")
        self.settings = settings
        self.controller = self.create_controller()
        self.server = TcpServer(self.settings.port or DEFAULT_PORT, self._on_new_connection)
        self.clock = pygame.time.Clock()
        self.running = True
        self._lock = threading.RLock()
        self.__coordinators: dict[int, Address] = {}
        self.__processes: dict[int, Process] = {}

    def create_controller(lobby_coordinator: 'LobbyCoordinator'):
        from tic_tac_toe.controller import LobbyEventHandler

        class Controller(LobbyEventHandler):
            def on_create_game(self, **kwargs):
                game_id = max(lobby_coordinator.coordinators.keys(), default=0) + 1
                lobby_connection, coordinator_connection = Pipe()
                process: Process = Process(
                    target=main_coordinator,
                    args=(game_id, coordinator_connection, lobby_coordinator.settings),
                    daemon=True
                )
                process.start()
                coordinator_address = lobby_connection.recv()
                lobby_coordinator.add_process(game_id, process)
                lobby_coordinator.add_coordinator(game_id, coordinator_address)
                if "connection" in kwargs:
                    connection: TcpConnection = kwargs["connection"]
                    connection.send(serialize({"coordinator": (connection.local_address.ip, coordinator_address.port)}))

            def on_delete_game(self, game_id: int):
                lobby_coordinator.remove_coordinator_by_id(game_id)
                lobby_coordinator.kill_process_by_id(game_id)

            def on_join_game(self, game_id: int, **kwargs):
                connection: TcpConnection = kwargs["connection"] if "connection" in kwargs else None
                if game_id in lobby_coordinator.coordinators.keys():
                    if connection is not None:
                        connection.send(serialize({"coordinator": (connection.local_address.ip, lobby_coordinator.coordinators[game_id].port)}))
                else:
                    error = f"Game {game_id} does not exist! Impossible to join."
                    lobby_coordinator.logger.debug(error)
                    if connection is not None:
                        connection.send(serialize({"error": error}))

        return Controller()

    @property
    def coordinators(self) -> Dict[int, Address]:
        with self._lock:
            return self.__coordinators

    @coordinators.setter
    def coordinators(self, coordinators: Dict[int, Address]):
        with self._lock:
            self.__coordinators = coordinators

    def add_coordinator(self, game_id: int, address: Address):
        with self._lock:
            self.__coordinators.update({game_id: address})

    def remove_coordinator_by_id(self, game_id: int):
        with self._lock:
            self.__coordinators.pop(game_id)

    def add_process(self, game_id: int, process: Process):
        with self._lock:
            self.__processes.update({game_id: process})

    def kill_process_by_id(self, game_id: int):
        with self._lock:
            process: Process = self.__processes.pop(game_id, default=None)
            if process is not None and process.is_alive():
                process.kill()

    def before_run(self):
        pygame.init()

    def after_run(self):
        pygame.quit()

    def run(self):
        try:
            self.before_run()
            while self.running:
                self.controller.handle_events()
        finally:
            self.after_run()

    def stop(self):
        self.running = False

    def _on_new_connection(self, event: ServerEvent, connection: TcpConnection, address: Address, error: Exception):
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

    def _on_message_received(self, event: ConnectionEvent, payload: str, connection: TcpConnection, error: Exception):
        match event:
            case ConnectionEvent.MESSAGE:
                if payload is not None:
                    self.__handle_message(deserialize(payload))
            case ConnectionEvent.CLOSE:
                self.logger.debug(f"Connection with coordinator {connection.remote_address} closed")
            case ConnectionEvent.ERROR:
                self.logger.debug(error)

    def __handle_message(self, message: Any, **kwargs):
        self.logger.debug(f"Message: {message}")
        if LobbyEvent.CREATE_GAME.matches(message) or LobbyEvent.JOIN_GAME.matches(message):
            message.connection = kwargs["connection"]
        pygame.event.post(message)

class TicTacToeCoordinator(TicTacToeGame):

    def __init__(self, game_id: int, settings: Settings=None):
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
            def render(self):
                event = coordinator.controller.create_event(ControlEvent.TIME_ELAPSED, dt=coordinator.dt, status=self._tic_tac_toe)
                coordinator._broadcast_to_all_peers(event)

        return SendToPeersTicTacToeView(coordinator.tic_tac_toe)

    def create_controller(coordinator: 'TicTacToeCoordinator'):
        from tic_tac_toe.controller.local import TicTacToeEventHandler, InputHandler

        class Controller(TicTacToeEventHandler, InputHandler):
            def __init__(self, tic_tac_toe: TicTacToe):
                TicTacToeEventHandler.__init__(self, tic_tac_toe)

            def on_player_join(self, tic_tac_toe: TicTacToe, symbol: Symbol, **kwargs):
                try:
                    super().on_player_join(tic_tac_toe, symbol=symbol)
                except ValueError as exception:
                    if "connection" in kwargs:
                        connection: TcpConnection = kwargs["connection"]
                        connection.send(serialize({"error": str(exception)}))

            def on_player_leave(self, tic_tac_toe: TicTacToe, symbol: Symbol):
                self.on_game_over(tic_tac_toe, symbol=None)

            def on_game_over(self, tic_tac_toe: TicTacToe, symbol: Symbol):
                super().on_game_over(tic_tac_toe, symbol)
                self.post_event(LobbyEvent.DELETE_GAME, game_id=coordinator.game_id)
                coordinator.stop()

            def handle_inputs(self, dt: float=None):
                self.time_elapsed(dt)

            def handle_events(self):
                game_over_events: List[Event] = pygame.event.get(ControlEvent.GAME_OVER.value)
                if len(game_over_events) > 0:
                    event = game_over_events.pop()
                    coordinator._broadcast_to_all_peers(event)
                    self.on_game_over(tic_tac_toe=self._tic_tac_toe, symbol=event.symbol)
                super().handle_events()

        return Controller(coordinator.tic_tac_toe)

    def at_each_run(self):
        pass

    def after_run(self):
        super().after_run()
        self.server.close()

    @property
    def peers(self) -> Set[Address]:
        with self._lock:
            return set(self._peers)

    @peers.setter
    def peers(self, value: Iterable[Address]):
        with self._lock:
            self._peers = set(value)

    def add_peer(self, peer: Address):
        with self._lock:
            self._peers.add(peer)

    def remove_peer(self, peer: Address):
        with self._lock:
            if self._peers.__contains__(peer):
                self._peers.remove(peer)

    def _broadcast_to_all_peers(self, message: Any):
        event = serialize(message)
        for peer in self.peers:
                self.server.connections[peer].send(event)

    def _on_new_connection(self, event: ServerEvent, connection: TcpConnection, address: Address, error: Exception):
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

    def _on_message_received(self, event: ConnectionEvent, payload: str, connection: TcpConnection, error: Exception):
        match event:
            case ConnectionEvent.MESSAGE:
                if payload:
                    self.__handle_message(deserialize(payload), connection=connection)
            case ConnectionEvent.CLOSE:
                self.logger.debug(f"Connection with peer {connection.remote_address} closed")
                self.remove_peer((connection.remote_address.host, connection.remote_address.port))
                if self.tic_tac_toe.is_player_lobby_full():
                    self.controller.post_event(ControlEvent.GAME_OVER, symbol=None)
                self.tic_tac_toe.players.clear()
            case ConnectionEvent.ERROR:
                self.logger.debug(error)
                self.remove_peer((connection.remote_address.host, connection.remote_address.port))

    def __handle_message(self, message: Any, **kwargs):
        if isinstance(message, pygame.event.Event):
            if ControlEvent.PLAYER_JOIN.matches(message):
                message.connection = kwargs["connection"]
            elif ControlEvent.PLAYER_LEAVE.matches(message):
                self._broadcast_to_all_peers(message)
            pygame.event.post(message)
        elif isinstance(message, str):
            self._broadcast_to_all_peers(message)
            self.logger.debug(f"Received message: {message}")

class TicTacToeTerminal(TicTacToeGame):

    def __init__(self, symbol: Symbol, create_game: bool=False, game_id: Optional[int]=None, settings: Settings=None):
        settings = settings or Settings()
        self.create_game = create_game
        self.game_id = game_id
        self.logger = logger("Terminal")
        super().__init__(settings)
        self.client = TcpClient(Address(host=self.settings.host or DEFAULT_HOST, port=self.settings.port or DEFAULT_PORT))
        self.symbol = symbol
        self.connected_to_coordinator = False
        self._lock = threading.RLock()
        self._thread_receiver = threading.Thread(target=self._handle_ingoing_messages, daemon=True)
        self._thread_receiver.start()
        self._thread_sender = threading.Thread(target=self._send_message, daemon=True)
        self._thread_sender.start()

    def create_controller(terminal: 'TicTacToeTerminal'):
        from tic_tac_toe.controller.local import TicTacToeInputHandler, EventHandler

        class Controller(TicTacToeInputHandler, EventHandler):
            def __init__(self, tic_tac_toe: TicTacToe):
                TicTacToeInputHandler.__init__(self, tic_tac_toe)

            def mouse_clicked(self):
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

            def handle_inputs(self, dt: float=None):
                if terminal.connected_to_coordinator:
                    return super().handle_inputs(dt, terminal.symbol)
                else:
                    for event in pygame.event.get(pygame.KEYDOWN):
                        if event.key == pygame.K_ESCAPE:
                            self.post_event(ControlEvent.PLAYER_LEAVE, symbol=terminal.symbol)
                    pygame.event.clear(self.INPUT_EVENTS)

            def on_player_create_game(self):
                terminal.logger.debug(f"Requesting game creation from lobby")
                self.post_event(LobbyEvent.CREATE_GAME, symbol=terminal.symbol)

            def on_player_join_game(self, game_id: int):
                terminal.logger.debug(f"Requesting join game {game_id} from lobby")
                self.post_event(LobbyEvent.JOIN_GAME, game_id=game_id, symbol=terminal.symbol)

            def on_change_turn(self, tic_tac_toe: TicTacToe):
                tic_tac_toe.change_turn()
                tic_tac_toe.remove_random_mark()

            def on_time_elapsed(self, tic_tac_toe: TicTacToe, dt: float, status: TicTacToe=None): # type: ignore[override]
                if not status:
                    tic_tac_toe.update(dt)
                else:
                    tic_tac_toe.override(status)

            def on_player_leave(self, tic_tac_toe: TicTacToe, symbol: Symbol):
                if symbol != terminal.symbol:
                    print(f"You won because player '{symbol.value}' has left the game!")
                elif tic_tac_toe.is_player_lobby_full():
                    print(f"You lost because you left the game!")
                terminal.stop()

            def on_game_over(self, tic_tac_toe: TicTacToe, symbol: Symbol):
                if symbol:
                    print(f"You won!" if symbol == terminal.symbol else f"You lost!")
                else:
                    print("Game ended")
                terminal.stop()

        return Controller(terminal.tic_tac_toe)

    def _handle_ingoing_messages(self):
        while self.running:
            try:
                message = self.client.receive()
                if message is not None:
                    self.__handle_message(deserialize(message))
            except ConnectionResetError:
                if self.running:
                    self.logger.debug(f"Coordinator stopped")
                    self.controller.on_game_over(self.tic_tac_toe, None)

    def __handle_message(self, message: Any):
        if isinstance(message, pygame.event.Event):
            pygame.event.post(message)
        elif isinstance(message, dict):
            self.__handle_dict_message(message)
        elif isinstance(message, str):
            print(message)

    def __handle_dict_message(self, message: Dict):
        if "error" in message:
            self.logger.debug(message["error"])
            self.stop()
        elif "coordinator" in message:
            coord_address = Address(message["coordinator"][0], message["coordinator"][1])
            self.logger.debug(f"Received coordinator address {coord_address}")
            with self._lock:
                old_client = self.client
                old_client.close()
                self.client = TcpClient(coord_address)
                self.connected_to_coordinator = True
            self.controller.post_event(ControlEvent.PLAYER_JOIN, symbol=self.symbol)

    def before_run(self):
        super().before_run()
        if self.create_game:
            self.controller.post_event(ControlEvent.PLAYER_CREATE_GAME)
        elif self.game_id is not None:
            self.controller.post_event(ControlEvent.PLAYER_JOIN_GAME, game_id=self.game_id)

    def after_run(self):
        super().after_run()
        self.client.close()

    def _send_message(self):
        while self.running:
            try:
                msg = input()
                self.logger.debug(f"Send {msg} to the opponent")
                if msg is not None:
                    self.client.send(serialize(self.message(msg, f"Player '{self.symbol.value}'")))
            except (EOFError, KeyboardInterrupt):
                self.logger.debug("Error while sending the message")

    def message(self, text: str, sender: str, timestamp: datetime=None):
        if timestamp is None:
            timestamp = datetime.now()
        return f"[{timestamp.isoformat(timespec="minutes")}] {sender}: {text.strip()}"


def main_lobby(settings: Settings=None):
    LobbyCoordinator(settings).run()

def main_coordinator(game_id: int, connection: Connection, settings: Settings=None):
    coordinator = TicTacToeCoordinator(game_id, settings)
    connection.send(coordinator.server.address)
    connection.close()
    coordinator.run()

def main_terminal(symbol: Symbol, creation: bool=False, game_id: Optional[int]=None, settings: Settings=None):
    TicTacToeTerminal(symbol, creation, game_id, settings).run()
