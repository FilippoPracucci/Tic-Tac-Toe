from typing import Optional
from pygame.event import Event
import pygame
from tic_tac_toe.log import logger
from tic_tac_toe import TicTacToeGame
from tic_tac_toe.remote import *
from tic_tac_toe.utils import Settings
from tic_tac_toe.model import TicTacToe
from tic_tac_toe.model.game_object import Player, Symbol
from tic_tac_toe.controller import LobbyEvent, ControlEvent
from tic_tac_toe.remote.tcp import TcpClient, TcpConnection, TcpServer, Address
from tic_tac_toe.remote.presentation import serialize, deserialize
import threading


DEFAULT_HOST = "localhost"
DEFAULT_PORT = 12345


class LobbyCoordinator():

    def __init__(self, settings: Settings=None):
        self.settings = settings
        self.controller = self.create_controller()
        self.server = TcpServer(self.settings.port or DEFAULT_PORT, self._on_new_connection)
        self.clock = pygame.time.Clock()
        self.running = True
        self._lock = threading.RLock()
        self.__games: dict[int, TicTacToeGame] = {}
        self.__coordinators: dict[int, Address] = {}

    def create_controller(lobby_coordinator):
        from tic_tac_toe.controller import LobbyEventHandler

        class Controller(LobbyEventHandler):
            def on_create_game(self, connection: TcpConnection=None):
                game_id = max(lobby_coordinator.games.keys(), default=0) + 1
                coordinator: TicTacToeCoordinator = main_coordinator(game_id, settings=lobby_coordinator.settings)
                lobby_coordinator.add_game(coordinator)
                lobby_coordinator.add_coordinator(game_id, coordinator.server.address)
                if connection:
                    connection.send(serialize({"coordinator": (connection.local_address.ip, coordinator.server.address.port)}))

            def on_delete_game(self, game_id: int):
                lobby_coordinator.remove_game_by_id(game_id)
                lobby_coordinator.remove_coordinator_by_id(game_id)
                if len(lobby_coordinator.games) == 0:
                    lobby_coordinator.stop()

            def on_join_game(self, game_id: int, symbol: Symbol, connection: TcpConnection=None):
                    if game_id not in lobby_coordinator.games:
                        logger.error(f"Game {game_id} does not exist")
                        if connection:
                            connection.send(serialize({"error": "Game not found"}))
                        return
                    lobby_coordinator.games[game_id].tic_tac_toe.add_player(Player(symbol))
                    if connection:
                        connection.send(serialize({"coordinator": (connection.local_address.ip, lobby_coordinator.coordinators[game_id].port)}))

            def on_leave_game(self, game_id: int, symbol: Symbol):
                game_to_leave: TicTacToeGame = lobby_coordinator.game_by_id(game_id)
                game_to_leave.tic_tac_toe.add_player(Player(symbol))

        return Controller()

    @property
    def games(self) -> dict[int, TicTacToeGame]:
        return self.__games

    @games.setter
    def games(self, games: dict[int, TicTacToeGame]):
        self.__games = games

    def add_game(self, game: TicTacToeGame):
        self.games[len(self.games)] = game

    def remove_game_by_id(self, id: int):
        self.__games.pop(id)

    def game_by_id(self, game_id: int) -> TicTacToeGame:
        assert self.games.__contains__(game_id), f"Game with id {game_id} not present"
        return self.games.get(game_id)

    @property
    def coordinators(self) -> dict[int, Address]:
        with self._lock:
            return self.__coordinators

    @coordinators.setter
    def coordinators(self, coordinators: dict[int, Address]):
        with self._lock:
            self.__coordinators = coordinators

    def add_coordinator(self, game_id: int, address: Address):
        with self._lock:
            self.__coordinators.update({game_id: address})

    def remove_coordinator_by_id(self, game_id: int):
        with self._lock:
            self.__coordinators.pop(game_id)

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

    def _on_new_connection(self, event: ServerEvent, connection: TcpConnection, address: Address, error):
        match event:
            case ServerEvent.LISTEN:
                logger.debug(f"Server listening on port {address.port} at {address.ip}")
            case ServerEvent.CONNECT:
                logger.debug(f"Open ingoing connection from: {address}")
                connection.callback = self._on_message_received
            case ServerEvent.STOP:
                logger.debug(f"Stop listening for new connections")
            case ServerEvent.ERROR:
                logger.debug(error)

    def _on_message_received(self, event: ConnectionEvent, payload, connection: TcpConnection, error):
        match event:
            case ConnectionEvent.MESSAGE:
                if payload:
                    payload = deserialize(payload)
                    if LobbyEvent.CREATE_GAME.matches(payload):
                        self.controller.on_create_game(connection=connection)
                    elif LobbyEvent.JOIN_GAME.matches(payload):
                        self.controller.on_join_game(
                            game_id=payload.dict.get('game_id'),
                            connection=connection
                        )
                    else:
                        pygame.event.post(payload)
            case ConnectionEvent.CLOSE:
                logger.debug(f"Connection with coordinator {connection.remote_address} closed")
                (id, _) = filter(lambda c: c[1].server.address == connection.remote_address, self.coordinators)[0]
                self.controller.post_event(LobbyEvent.DELETE_GAME, game_id=id)
            case ConnectionEvent.ERROR:
                logger.debug(error)
                (id, _) = filter(lambda c: c[1].server.address == connection.remote_address, self.coordinators)[0]
                self.controller.post_event(LobbyEvent.DELETE_GAME, game_id=id)

class TicTacToeCoordinator(TicTacToeGame):

    def __init__(self, game_id: int, settings: Settings = None):
        settings = settings or Settings()
        super().__init__(settings)
        self.game_id = game_id
        self.server = TcpServer(Address.any_local_port().port, self._on_new_connection)
        self._peers: set[Address] = set()
        self._lock = threading.RLock()

    def create_view(coordinator):
        from tic_tac_toe.view import ShowNothingTicTacToeView
        from tic_tac_toe.controller.local import ControlEvent

        class SendToPeersTicTacToeView(ShowNothingTicTacToeView):
            def render(self):
                event = coordinator.controller.create_event(ControlEvent.TIME_ELAPSED, dt=coordinator.dt, status=self._tic_tac_toe)
                coordinator._broadcast_to_all_peers(event)

        return SendToPeersTicTacToeView(coordinator.tic_tac_toe)

    def create_controller(coordinator):
        from tic_tac_toe.controller.local import TicTacToeEventHandler, InputHandler

        class Controller(TicTacToeEventHandler, InputHandler):
            def __init__(self, tic_tac_toe: TicTacToe):
                TicTacToeEventHandler.__init__(self, tic_tac_toe)

            def on_player_leave(self, tic_tac_toe: TicTacToe, symbol: Symbol):
                if not tic_tac_toe.is_player_lobby_full():
                    super().on_player_leave(tic_tac_toe, symbol=symbol)
                    self.post_event(LobbyEvent.LEAVE_GAME, game_id=coordinator.game_id, symbol=symbol)
                else:
                    self.on_game_over(tic_tac_toe, symbol=None)

            def on_game_over(self, tic_tac_toe: TicTacToe, symbol: Symbol):
                super().on_game_over(tic_tac_toe, symbol)
                self.post_event(LobbyEvent.DELETE_GAME, game_id=coordinator.game_id)
                coordinator.stop()

            def handle_inputs(self, dt=None):
                self.time_elapsed(dt)

        return Controller(coordinator.tic_tac_toe)

    def at_each_run(self):
        pass

    def after_run(self):
        super().after_run()
        self.server.close()

    @property
    def peers(self):
        with self._lock:
            return set(self._peers)

    @peers.setter
    def peers(self, value):
        with self._lock:
            self._peers = set(value)

    def add_peer(self, peer):
        with self._lock:
            self._peers.add(peer)

    def remove_peer(self, peer):
        with self._lock:
            if self._peers.__contains__(peer):
                self._peers.remove(peer)

    def _broadcast_to_all_peers(self, message):
        event = serialize(message)
        for peer in self.peers:
                self.server.connections[peer].send(event)

    def _on_new_connection(self, event: ServerEvent, connection: TcpConnection, address: Address, error):
        match event:
            case ServerEvent.LISTEN:
                logger.debug(f"Server listening on port {address.port} at {address.ip}")
            case ServerEvent.CONNECT:
                logger.debug(f"Open ingoing connection from: {address}")
                self.add_peer(address)
                connection.callback = self._on_message_received
            case ServerEvent.STOP:
                logger.debug(f"Stop listening for new connections")
            case ServerEvent.ERROR:
                logger.debug(error)

    def _on_message_received(self, event: ConnectionEvent, payload, connection: TcpConnection, error):
        match event:
            case ConnectionEvent.MESSAGE:
                if payload:
                    payload = deserialize(payload)
                    assert isinstance(payload, pygame.event.Event), f"Expected {pygame.event.Event}, got {type(payload)}"
                    pygame.event.post(payload)
                    self._broadcast_to_all_peers(payload)
            case ConnectionEvent.CLOSE:
                logger.debug(f"Connection with peer {connection.remote_address} closed")
                self.remove_peer((connection.remote_address.host, connection.remote_address.port))
                if self.tic_tac_toe.is_player_lobby_full():
                    self.controller.post_event(ControlEvent.GAME_OVER, symbol=None)
                self.tic_tac_toe.players = []
            case ConnectionEvent.ERROR:
                logger.debug(error)
                self.remove_peer((connection.remote_address.host, connection.remote_address.port))

class TicTacToeTerminal(TicTacToeGame):

    def __init__(self, symbol: Symbol, create_game: bool=False, game_id: Optional[int]=None, settings: Settings=None):
        settings = settings or Settings()
        self.create_game = create_game
        self.game_id = game_id
        super().__init__(settings)
        self.client = TcpClient(Address(host=self.settings.host or DEFAULT_HOST, port=self.settings.port or DEFAULT_PORT))
        self.symbol = symbol
        self.connected_to_coordinator = False
        self._thread_receiver = threading.Thread(target=self._handle_ingoing_messages, daemon=True)
        self._thread_receiver.start()

    def create_controller(terminal):
        from tic_tac_toe.controller.local import TicTacToeInputHandler, EventHandler

        class Controller(TicTacToeInputHandler, EventHandler):
            def __init__(self, tic_tac_toe: TicTacToe):
                TicTacToeInputHandler.__init__(self, tic_tac_toe)

            def mouse_clicked(self):
                pos = self._command.click().__getattribute__("click_point")
                self.post_event(ControlEvent.MARK_PLACED, cell=self._to_cell(pos), symbol=terminal.symbol)

            def post_event(self, event: Event | LobbyEvent | ControlEvent, **kwargs):
                pygame_event = super().post_event(event, **kwargs)
                if isinstance(event, LobbyEvent) \
                    or terminal.connected_to_coordinator and not ControlEvent.TIME_ELAPSED.matches(pygame_event):
                    terminal.client.send(serialize(pygame_event))
                return pygame_event

            def handle_inputs(self, dt=None):
                if terminal.tic_tac_toe.is_player_lobby_full():
                    return super().handle_inputs(dt, terminal.symbol)
                else:
                    for event in pygame.event.get(pygame.KEYDOWN):
                        if event.key == pygame.K_ESCAPE:
                            self.post_event(ControlEvent.PLAYER_LEAVE, symbol=terminal.symbol)
                    pygame.event.clear(self.INPUT_EVENTS)

            def on_player_create_game(self):
                logger.debug(f"Requesting game creation from lobby")
                self.post_event(LobbyEvent.CREATE_GAME)

            def on_player_join_game(self, game_id: int):
                logger.debug(f"Requesting join game {game_id} from lobby")
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
                print(f"Player '{symbol.value}' has left")
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
                message = deserialize(message)
                if isinstance(message, dict) and "coordinator" in message:
                    coord_address = Address(message["coordinator"][0], message["coordinator"][1])
                    self.client.close()
                    self.client = TcpClient(coord_address)
                    self.connected_to_coordinator = True
                    self.controller.post_event(ControlEvent.PLAYER_JOIN, symbol=self.symbol)
                elif isinstance(message, pygame.event.Event):
                    pygame.event.post(message)
            except ConnectionResetError:
                if self.running:
                    logger.debug(f"Coordinator stopped")
                    self.controller.on_game_over(self.tic_tac_toe, None)

    def before_run(self):
        super().before_run()
        if self.create_game:
            self.controller.post_event(ControlEvent.PLAYER_CREATE_GAME)
        elif self.game_id is not None:
            self.controller.post_event(ControlEvent.PLAYER_JOIN_GAME, game_id=self.game_id)
        # self.controller.post_event(ControlEvent.PLAYER_JOIN, game_id=self.game_id, symbol=self.symbol)

    def after_run(self):
        super().after_run()
        self.client.close()


def main_lobby(settings: Settings=None):
    LobbyCoordinator(settings).run()

def main_coordinator(game_id: int, settings: Settings=None) -> TicTacToeCoordinator:
    coordinator = TicTacToeCoordinator(game_id, settings)
    threading.Thread(target=coordinator.run, daemon=True).start()
    return coordinator

def main_terminal(symbol: Symbol, creation: bool=False, game_id: Optional[int]=None, settings: Settings=None):
    TicTacToeTerminal(symbol, creation, game_id, settings).run()
