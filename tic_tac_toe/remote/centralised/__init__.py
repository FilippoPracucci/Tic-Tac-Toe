from pygame.event import Event
import pygame
from tic_tac_toe import TicTacToeGame
from tic_tac_toe.remote import *
from tic_tac_toe.utils import Settings
from tic_tac_toe.model import TicTacToe
from tic_tac_toe.model.game_object import Symbol, Mark
from tic_tac_toe.model.grid import Cell
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
        """ self._thread_receiver = threading.Thread(target=__handle_incoming_connections, daemon=True)
        self._thread_receiver.start() """
        self._peers: set[Address] = set()
        self._lock = threading.RLock()

    def create_view(coordinator):
        from tic_tac_toe.view import ShowNothingTicTacToeView
        from tic_tac_toe.controller.local import ControlEvent

        class SendToPeersTicTacToeView(ShowNothingTicTacToeView):
            def render(self, marks):
                pass
                """ event = coordinator.controller.create_event(ControlEvent.TIME_ELAPSED, dt=coordinator.dt, status=self._tic_tac_toe) # removed status=self._pong (taken from PongView)
                coordinator._broadcast_to_all_peers(event) """

        return SendToPeersTicTacToeView(
            coordinator.tic_tac_toe.config.cell_width_size,
            coordinator.tic_tac_toe.config.cell_height_size,
            coordinator.tic_tac_toe.grid.dim
        )

    def create_controller(coordinator):
        from tic_tac_toe.controller.local import TicTacToeEventHandler, InputHandler

        class Controller(TicTacToeEventHandler, InputHandler):
            def __init__(self, tic_tac_toe: TicTacToe):
                TicTacToeEventHandler.__init__(self, tic_tac_toe)

            def on_player_join(self, tic_tac_toe: TicTacToe):
                super().on_player_join(tic_tac_toe)

            def on_player_leave(self, tic_tac_toe: TicTacToe, symbol: Symbol):
                """ for mark in filter(lambda m: m.symbol == symbol, tic_tac_toe.marks):
                    tic_tac_toe.remove_mark(mark.cell) """
                self.on_game_over()
                #self.post_event(ControlEvent.GAME_OVER)

            def on_game_over(self):
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
            self.server.send(payload=event, address=peer)

    def _on_new_connection(self, event: ServerEvent, connection: TcpConnection, address: Address, error):
        match event:
            case ServerEvent.LISTEN:
                print(f"Server listening on port {address.port} at {address.ip}")
            case ServerEvent.CONNECT:
                print(f"Open ingoing connection from: {address}")
                self.add_peer(address)
                connection.callback = self._on_message_received
            case ServerEvent.STOP:
                print(f"Stop listening for new connections")
            case ServerEvent.ERROR:
                print(error)

    def _on_message_received(self, event: ConnectionEvent, payload, connection: TcpConnection, error):
        match event:
            case ConnectionEvent.MESSAGE:
                self._handle_ingoing_messages(payload)
            case ConnectionEvent.CLOSE:
                print(f"Connection with peer {connection.remote_address} closed")
            case ConnectionEvent.ERROR:
                print(error)

    def _handle_ingoing_messages(self, payload):
        message = deserialize(payload)
        assert isinstance(message, pygame.event.Event), f"Expected {pygame.event.Event}, got {type(message)}"
        pygame.event.post(message)


class TicTacToeTerminal(TicTacToeGame):

    def __init__(self, settings: Settings = None):
        settings = settings or Settings()
        super().__init__(settings)
        self.client = TcpClient(Address(host=self.settings.host or DEFAULT_HOST, port=self.settings.port or DEFAULT_PORT))
        """ self._thread_receiver = threading.Thread(target=self._handle_ingoing_messages, daemon=True)
        self._thread_receiver.start() """

    def create_controller(terminal):
        from tic_tac_toe.controller.local import TicTacToeInputHandler, EventHandler

        class Controller(TicTacToeInputHandler, EventHandler):
            def __init__(self, tic_tac_toe: TicTacToe):
                TicTacToeInputHandler.__init__(self, tic_tac_toe)

            def post_event(self, event: Event | ControlEvent, **kwargs):
                event = super().post_event(event, **kwargs)
                terminal.client.send(serialize(event))
                return event

            def handle_inputs(self, dt=None):
                return super().handle_inputs(dt)

            def handle_events(self):
                return super().handle_events()

            def on_mark_placed(self, tic_tac_toe: TicTacToe, cell: Cell):
                tic_tac_toe.place_mark(Mark(
                    cell=cell,
                    symbol=tic_tac_toe.turn,
                    size=(tic_tac_toe.size / tic_tac_toe.grid.dim),
                    position=tic_tac_toe.config.cells_symbol_position.get((cell.x, cell.y))
                ))
                """ if tic_tac_toe.place_mark(Mark(
                    cell,
                    self._tic_tac_toe.turn,
                    tic_tac_toe.size.x / tic_tac_toe.grid.dim,
                    tic_tac_toe.config.cells_symbol_position.get((cell.x, cell.y))
                )):
                    if tic_tac_toe.has_won(tic_tac_toe.turn):
                        self.on_game_over(tic_tac_toe)
                    tic_tac_toe.change_turn()
                    tic_tac_toe.remove_random_mark() """

            def on_change_turn(self, tic_tac_toe):
                if tic_tac_toe.has_won(tic_tac_toe.turn):
                    #self.on_game_over(tic_tac_toe)
                    self.post_event(ControlEvent.GAME_OVER)
                tic_tac_toe.change_turn()
                tic_tac_toe.remove_random_mark()

            def on_time_elapsed(self, tic_tac_toe: TicTacToe, dt: float, status: TicTacToe=None): # type: ignore[override]
                pass
                """ if not status:
                    tic_tac_toe.update(dt)
                else:
                    tic_tac_toe.override(status) """

            def on_player_leave(self, tic_tac_toe: TicTacToe, symbol: Symbol):
                terminal.stop()
        
        return Controller(terminal.tic_tac_toe)
    
    def _handle_ingoing_messages(self):
        while self.running:
            message = self.client.receive()
            if message is not None:
                message = deserialize(message)
                assert isinstance(message, pygame.event.Event), f"Expected {pygame.event.Event}, got {type(message)}"
                pygame.event.post(message)

    def before_run(self):
        super().before_run()
        self.controller.post_event(ControlEvent.PLAYER_JOIN)

    def after_run(self):
        super().after_run()
        self.client.close()


def main_coordinator(settings = None):
    TicTacToeCoordinator(settings).run()


def main_terminal(settings = None):
    TicTacToeTerminal(settings).run()
