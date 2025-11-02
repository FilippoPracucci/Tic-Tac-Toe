from pygame.event import Event
import pygame
from tic_tac_toe.log import logger
from tic_tac_toe import TicTacToeGame
from tic_tac_toe.remote import *
from tic_tac_toe.utils import Settings
from tic_tac_toe.model import TicTacToe
from tic_tac_toe.model.game_object import Player, Symbol
from tic_tac_toe.controller import ControlEvent
from tic_tac_toe.remote.tcp import TcpClient, TcpConnection, TcpServer, Address
from tic_tac_toe.remote.presentation import serialize, deserialize
import threading


DEFAULT_HOST = "localhost"
DEFAULT_PORT = 12345


class TicTacToeCoordinator(TicTacToeGame):

    def __init__(self, settings: Settings = None):
        settings = settings or Settings()
        super().__init__(settings)
        self.server = TcpServer(self.settings.port or DEFAULT_PORT, self._on_new_connection)
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

            def on_player_leave(self, tic_tac_toe: TicTacToe, player: Player):
                self.on_game_over(tic_tac_toe, player=None)

            def on_game_over(self, tic_tac_toe: TicTacToe, player: Player):
                super().on_game_over(tic_tac_toe, player)
                coordinator._broadcast_to_all_peers(self.create_event(ControlEvent.GAME_OVER, player=player))
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

    def _broadcast_to_all_peers(self, message):
        event = serialize(message)
        for peer in self.peers:
                self.server.connections[peer].send(event)

    def _on_new_connection(self, event: ServerEvent, connection: TcpConnection, address: Address, error):
        match event:
            case ServerEvent.LISTEN:
                logger.info(f"Server listening on port {address.port} at {address.ip}")
            case ServerEvent.CONNECT:
                logger.info(f"Open ingoing connection from: {address}")
                self.add_peer(address)
                connection.callback = self._on_message_received
            case ServerEvent.STOP:
                logger.info(f"Stop listening for new connections")
            case ServerEvent.ERROR:
                logger.error(error)

    def _on_message_received(self, event: ConnectionEvent, payload, connection: TcpConnection, error):
        match event:
            case ConnectionEvent.MESSAGE:
                if payload:
                    payload = deserialize(payload)
                    assert isinstance(payload, pygame.event.Event), f"Expected {pygame.event.Event}, got {type(payload)}"
                    pygame.event.post(payload)
                    self._broadcast_to_all_peers(payload)
            case ConnectionEvent.CLOSE:
                logger.info(f"Connection with peer {connection.remote_address} closed")
            case ConnectionEvent.ERROR:
                logger.error(error)

class TicTacToeTerminal(TicTacToeGame):

    def __init__(self, symbol: Symbol, settings: Settings = None):
        settings = settings or Settings()
        super().__init__(settings)
        self.client = TcpClient(Address(host=self.settings.host or DEFAULT_HOST, port=self.settings.port or DEFAULT_PORT))
        self.symbol = symbol
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

            def post_event(self, event: Event | ControlEvent, **kwargs):
                event = super().post_event(event, **kwargs)
                if not ControlEvent.TIME_ELAPSED.matches(event):
                    terminal.client.send(serialize(event))
                return event

            def handle_inputs(self, dt=None):
                return super().handle_inputs(dt)

            """ def handle_events(self):
                # terminal._handle_ingoing_messages()
                super().handle_events() """

            def on_change_turn(self, tic_tac_toe: TicTacToe):
                tic_tac_toe.change_turn()
                tic_tac_toe.remove_random_mark()

            def on_time_elapsed(self, tic_tac_toe: TicTacToe, dt: float, status: TicTacToe=None): # type: ignore[override]
                if not status:
                    tic_tac_toe.update(dt)
                else:
                    tic_tac_toe.override(status)

            def on_player_leave(self, tic_tac_toe: TicTacToe, player: Player):
                terminal.stop()

            def on_game_over(self, tic_tac_toe: TicTacToe, player: Player):
                if player:
                    print(f"You won!" if player.symbol == terminal.symbol else f"You lost!")
                else:
                    print("Game ended")
                terminal.stop()

        return Controller(terminal.tic_tac_toe)

    def _handle_ingoing_messages(self):
        while self.running:
            try:
                message = self.client.receive()
                message = deserialize(message)
                assert isinstance(message, pygame.event.Event), f"Expected {pygame.event.Event}, got {type(message)}"
                pygame.event.post(message)
            except ConnectionResetError:
                if self.running:
                    print(f"Coordinator stopped")
                    self.controller.on_game_over(self.tic_tac_toe, None)

    def before_run(self):
        super().before_run()
        self.controller.post_event(ControlEvent.PLAYER_JOIN, symbol=self.symbol)

    def after_run(self):
        super().after_run()
        self.client.close()


def main_coordinator(settings = None):
    TicTacToeCoordinator(settings).run()


def main_terminal(symbol: Symbol, settings = None):
    TicTacToeTerminal(symbol, settings).run()
