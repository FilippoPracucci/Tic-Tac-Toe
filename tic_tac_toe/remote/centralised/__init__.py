from datetime import datetime
from multiprocessing import Pipe, Pool
from queue import Queue
from typing import Any, Dict, Iterable, List
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
import threading, json, os
from tic_tac_toe.view import LobbyMenu

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 12345
GAME_IDS_FILE = "games.json"


class LobbyCoordinator():

    def __init__(self, settings: Settings=None):
        self.logger = logger("LobbyCoordinator")
        self.settings = settings
        self.controller = self.create_controller()
        self.server = TcpServer(self.settings.port or DEFAULT_PORT, self._on_new_connection)
        self.clock = pygame.time.Clock()
        self.running = True
        self._processes_pool = Pool()
        self._lock = threading.RLock()
        self.__coordinators: Dict[int, Address] = {}
        self.__joinable_games: Dict[int, str] = {}
        self.__game_ids_subscribers: Dict[Address, TcpConnection] = {}
        open(GAME_IDS_FILE, "x")

    def create_controller(lobby_coordinator: 'LobbyCoordinator'):
        from tic_tac_toe.controller import LobbyEventHandler

        class Controller(LobbyEventHandler):
            def on_create_game(self, **kwargs):
                game_id = max(lobby_coordinator.game_ids(), default=0) + 1
                lobby_connection, coordinator_connection = Pipe()
                lobby_coordinator._processes_pool.apply_async(
                    func=main_coordinator,
                    args=(game_id, coordinator_connection, lobby_coordinator.settings),
                    callback=lambda _: self.on_delete_game(game_id)
                )
                coordinator_address = lobby_connection.recv()
                lobby_coordinator.add_coordinator(game_id, coordinator_address)
                if "symbol" in kwargs:
                    lobby_coordinator.add_joinable_game(game_id, str(self.__opposite_symbol(kwargs["symbol"]).value))
                self.__update_and_broadcast_game_ids()
                if "connection" in kwargs:
                    connection: TcpConnection = kwargs["connection"]
                    connection.send(serialize({"coordinator": (connection.local_address.ip, coordinator_address.port)}))

            def on_delete_game(self, game_id: int):
                lobby_coordinator.remove_coordinator_by_id(game_id)
                lobby_coordinator.remove_joinable_game(game_id)
                self.__update_and_broadcast_game_ids()

            def on_join_game(self, game_id: int, **kwargs):
                connection: TcpConnection = kwargs["connection"] if "connection" in kwargs else None
                lobby_coordinator.remove_joinable_game(game_id)
                self.__update_and_broadcast_game_ids()
                if game_id in lobby_coordinator.game_ids():
                    if connection is not None:
                        connection.send(serialize({"coordinator": (connection.local_address.ip, lobby_coordinator.coordinators[game_id].port)}))
                else:
                    error = f"Game {game_id} does not exist! Impossible to join."
                    lobby_coordinator.logger.debug(error)
                    if connection is not None:
                        connection.send(serialize({"error": error}))

            def on_request_joinable_game_ids(self, **kwargs):
                connection: TcpConnection = kwargs["connection"] if "connection" in kwargs else None
                if connection is not None:
                    self.__init_game_ids()
                    connection.send(serialize({"game_ids": lobby_coordinator.joinable_games()}))
                    lobby_coordinator.add_game_ids_subscriber(connection)

            def __broadcast_game_ids(self):
                for connection in lobby_coordinator.game_ids_subscribers():
                    try:
                        connection.send(serialize({"game_ids": lobby_coordinator.joinable_games()}))
                    except Exception as e:
                        lobby_coordinator.logger.debug(f"Error while broadcasting game IDs to {connection.remote_address}")

            def __update_games_id_db(self):
                with open(GAME_IDS_FILE, "w") as file:
                    json.dump(lobby_coordinator.joinable_games(), file)

            def __update_and_broadcast_game_ids(self):
                self.__update_games_id_db()
                self.__broadcast_game_ids()

            def __init_game_ids(self):
                with open(GAME_IDS_FILE, "r") as file:
                    try:
                        self.joinable_games = dict(map(lambda k, v: (int(k), str(self.__opposite_symbol(Symbol(v)).value)), json.load(file)))
                    except:
                        self.joinable_games = []

            def __opposite_symbol(self, symbol: Symbol) -> Symbol:
                return Symbol.NOUGHT if symbol.is_cross else Symbol.CROSS

        return Controller()

    @property
    def coordinators(self) -> Dict[int, Address]:
        with self._lock:
            return self.__coordinators

    @coordinators.setter
    def coordinators(self, coordinators: Dict[int, Address]):
        with self._lock:
            self.__coordinators = coordinators

    def game_ids(self) -> List[int]:
        return list(self.coordinators.keys())

    def joinable_games(self) -> Dict[int, str]:
        return self.__joinable_games

    def add_joinable_game(self, game_id: int, symbol: str):
        with self._lock:
            self.__joinable_games[game_id] = symbol

    def remove_joinable_game(self, game_id: int):
        with self._lock:
            self.__joinable_games.pop(game_id)

    def add_coordinator(self, game_id: int, address: Address):
        with self._lock:
            self.__coordinators.update({game_id: address})

    def remove_coordinator_by_id(self, game_id: int):
        with self._lock:
            self.__coordinators.pop(game_id)

    def add_game_ids_subscriber(self, connection: TcpConnection):
        with self._lock:
            self.__game_ids_subscribers[connection.remote_address] = connection

    def remove_game_ids_subscriber_by_address(self, address: Address):
        with self._lock:
            if address in self.__game_ids_subscribers:
                self.__game_ids_subscribers.pop(address)

    def game_ids_subscribers(self) -> List[TcpConnection]:
        with self._lock:
            return list(self.__game_ids_subscribers.values())

    def before_run(self):
        pygame.init()

    def after_run(self):
        pygame.quit()
        os.remove(GAME_IDS_FILE)

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
                    self.__handle_message(deserialize(payload), connection=connection)
            case ConnectionEvent.CLOSE:
                self.logger.debug(f"Connection with coordinator {connection.remote_address} closed")
                self.remove_game_ids_subscriber_by_address(connection.remote_address)
            case ConnectionEvent.ERROR:
                self.logger.debug(error)
                self.remove_game_ids_subscriber_by_address(connection.remote_address)

    def __handle_message(self, message: Any, **kwargs):
        self.logger.debug(f"Message: {message}")
        if LobbyEvent.CREATE_GAME.matches(message) or \
            LobbyEvent.JOIN_GAME.matches(message) or \
            LobbyEvent.REQUEST_JOINABLE_GAME_IDS.matches(message):
            if "connection" in kwargs:
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
                self.on_game_over(tic_tac_toe)

            def on_game_over(self, tic_tac_toe: TicTacToe, **kwargs):
                super().on_game_over(tic_tac_toe, **kwargs)
                self.post_event(LobbyEvent.DELETE_GAME, game_id=coordinator.game_id)
                coordinator.stop()

            def handle_inputs(self, dt: float=None):
                self.time_elapsed(dt)

            def handle_events(self):
                game_over_events: List[Event] = pygame.event.get(ControlEvent.GAME_OVER.value)
                if game_over_events:
                    event = game_over_events.pop()
                    coordinator._broadcast_to_all_peers(event)
                    self.on_game_over(tic_tac_toe=self._tic_tac_toe, **event.dict)
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
                self.controller.post_event(ControlEvent.GAME_OVER)
                self.tic_tac_toe.players.clear()
            case ConnectionEvent.ERROR:
                self.logger.debug(error)
                self.remove_peer((connection.remote_address.host, connection.remote_address.port))

    def __handle_message(self, message: Any, **kwargs):
        if isinstance(message, pygame.event.Event):
            if ControlEvent.PLAYER_JOIN.matches(message):
                if "connection" in kwargs:
                    message.connection = kwargs["connection"]
            elif ControlEvent.PLAYER_LEAVE.matches(message):
                self._broadcast_to_all_peers(message)
            pygame.event.post(message)
        elif isinstance(message, str):
            self._broadcast_to_all_peers(message)
            self.logger.debug(f"Received message: {message}")

class TicTacToeTerminal(TicTacToeGame):

    def __init__(self, settings: Settings=None, lobby_menu: LobbyMenu=None, message_to_show: str=None):
        settings = settings or Settings()
        self.symbol: Symbol = None
        self.connected_to_coordinator = False
        self.joinable_game_ids: Dict[int, str] = {}
        self.joinable_games_updates: Queue[Dict[int, str]] = Queue()
        self._lobby_menu: LobbyMenu = lobby_menu
        self._message_to_show: str = message_to_show
        super().__init__(settings)
        self.logger = logger("Terminal")
        self.client = TcpClient(Address(host=self.settings.host or DEFAULT_HOST, port=self.settings.port or DEFAULT_PORT))
        self._lock = threading.RLock()
        self._thread_receiver = threading.Thread(target=self._handle_ingoing_messages, daemon=True)
        self._thread_receiver.start()
        self._thread_sender = threading.Thread(target=self._send_message, daemon=True)
        self._thread_sender.start()
        self.controller.post_event(LobbyEvent.REQUEST_JOINABLE_GAME_IDS)

    def wait_for_game_ids(self, timeout: float=None) -> Dict[int, str]:
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

            def on_player_create_game(self, symbol: Symbol):
                terminal.logger.debug(f"Requesting game creation from lobby")
                terminal.symbol = symbol
                terminal.view.title = f"Player {symbol.value}"
                self.post_event(LobbyEvent.CREATE_GAME, symbol=symbol)

            def on_player_join_game(self, symbol: Symbol, game_id: int):
                terminal.logger.debug(f"Requesting join game {game_id} from lobby")
                terminal.symbol = symbol
                terminal.view.title = f"Player {symbol.value}"
                self.post_event(LobbyEvent.JOIN_GAME, game_id=game_id, symbol=symbol)

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
                    terminal._message_to_show = f"You won because other player left the game!"
                elif tic_tac_toe.is_player_lobby_full():
                    terminal._message_to_show = f"You lost because you left the game!"
                if terminal._message_to_show is not None:
                    print(terminal._message_to_show)
                terminal.restart()

            def on_game_over(self, tic_tac_toe: TicTacToe, **kwargs):
                if "symbol" in kwargs:
                    terminal._message_to_show = f"You won!" if kwargs["symbol"] == terminal.symbol else f"You lost!"
                    print(terminal._message_to_show)
                    terminal.restart()
                else:
                    error_cause_message = terminal._message_to_show if terminal._message_to_show is not None else 'unexpected error'
                    print(f"Game ended: {error_cause_message}")
                    if terminal._lobby_menu is not None:
                        terminal._lobby_menu.stop()
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
                    self._message_to_show = "coordinator stopped"
                    self.logger.debug(self._message_to_show)
                    self.controller.on_game_over(self.tic_tac_toe)

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
        elif "game_ids" in message:
            self.joinable_game_ids = message["game_ids"]
            self.joinable_games_updates.put(self.joinable_game_ids)
        elif "coordinator" in message:
            coord_address = Address(message["coordinator"][0], message["coordinator"][1])
            self.logger.debug(f"Received coordinator address {coord_address}")
            with self._lock:
                old_client = self.client
                old_client.close()
                self.client = TcpClient(coord_address)
                self.connected_to_coordinator = True
            self.controller.post_event(ControlEvent.PLAYER_JOIN, symbol=self.symbol)

    def _callback_on_create_game(self, selected_symbol: Symbol):
        self.controller.post_event(ControlEvent.PLAYER_CREATE_GAME, symbol=selected_symbol)
        self._lobby_menu = None

    def _callback_on_join_game(self, selected_symbol: Symbol, selected_game_id: int):
        self.controller.post_event(ControlEvent.PLAYER_JOIN_GAME, symbol=selected_symbol, game_id=selected_game_id)
        self._lobby_menu = None

    def before_run(self):
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

    def restart(self):
        self.stop()
        main_terminal(self.settings, message_to_show=self._message_to_show)


def main_lobby(settings: Settings=None):
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    LobbyCoordinator(settings).run()

def main_coordinator(game_id: int, connection: Connection, settings: Settings=None):
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    coordinator = TicTacToeCoordinator(game_id, settings)
    connection.send(coordinator.server.address)
    connection.close()
    coordinator.run()

def main_terminal(settings: Settings=None, message_to_show: str=None):
    lobby_menu = LobbyMenu(size=settings.size)
    TicTacToeTerminal(settings, lobby_menu, message_to_show=message_to_show).run()
