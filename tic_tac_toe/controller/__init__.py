import pygame
from ..model import *
from dataclasses import dataclass, field
from enum import Enum
from tic_tac_toe.model import Symbol
from typing import Set

class LobbyEvent(Enum):
    """The enumeration of lobby-related pygame events."""

    CREATE_GAME = pygame.event.custom_type()
    DELETE_GAME = pygame.event.custom_type()
    JOIN_GAME = pygame.event.custom_type()
    REQUEST_JOINABLE_GAME_IDS = pygame.event.custom_type()

    @classmethod
    def all(cls) -> Set['LobbyEvent']:
        """Return all lobby events.

        :return: The complete set of lobby events.
        """
        return set(cls.__members__.values())

    @classmethod
    def all_types(cls) -> Set[int]:
        """Return the pygame event types used by all lobby events.

        :return: The set of integer pygame event identifiers.
        """
        return {event.value for event in cls.all()}

    @classmethod
    def is_lobby_event(cls, event: pygame.event.Event) -> bool:
        """Check whether an event is a lobby event.

        :param event: The pygame event to inspect.
        :return: `True` when the event matches one of the lobby events, `False` otherwise.
        """
        return any(lobby_event.matches(event) for lobby_event in cls.all())

    @classmethod
    def by_value(cls, value: int) -> 'LobbyEvent':
        """Lookup a lobby event by its pygame event type value.

        :param value: The event type.
        :return: The matching lobby event.
        :raise KeyError: When no matching lobby event is found.
        """
        for lobby_event in cls.all():
            if lobby_event.value == value:
                return lobby_event
        raise KeyError(f"{cls.__name__} with value {value} not found")

    def matches(self, event) -> bool:
        """Return whether the given object matches this lobby event.

        :param event: The object to check.
        :return: `True` when the provided object matches this event, `False` otherwise.
        """
        if isinstance(event, pygame.event.Event):
            return event.type == self.value
        elif isinstance(event, LobbyEvent):
            return event == self
        elif isinstance(event, int):
            return event == self.value
        return False

class ControlEvent(Enum):
    """Define the game-related events."""

    PLAYER_CREATE_GAME = pygame.event.custom_type()
    PLAYER_JOIN_GAME = pygame.event.custom_type()
    PLAYER_JOIN = pygame.event.custom_type()
    PLAYER_LEAVE = pygame.event.custom_type()
    GAME_START = pygame.event.custom_type()
    GAME_OVER = pygame.QUIT # TODO: change to a custom type (return to home page not quit)
    MARK_PLACED = pygame.event.custom_type()
    CHANGE_TURN = pygame.event.custom_type()
    TIME_ELAPSED = pygame.event.custom_type()

    @classmethod
    def all(cls) -> Set['ControlEvent']:
        """Return all control events.

        :return: The complete set of control events.
        """
        return set(cls.__members__.values())

    @classmethod
    def all_types(cls) -> Set[int]:
        """Return the pygame event types used by all control events.
        
        :return: The set of integer pygame event identifiers.
        """
        return {event.value for event in cls.all()}

    @classmethod
    def is_control_event(cls, event: pygame.event.Event) -> bool:
        """Check whether an event is a control event.
        
        :param event: The pygame event to inspect.
        :return: `True` when the event matches one of the control events, `False` otherwise.
        """
        return any(control_event.matches(event) for control_event in cls.all())

    @classmethod
    def by_value(cls, value: int) -> 'ControlEvent':
        """Lookup a control event by its pygame event type value.
        
        :param value: The event type.
        :return: The matching control event.
        :raise KeyError: When no matching control event is found.
        """
        for control_event in cls.all():
            if control_event.value == value:
                return control_event
        raise KeyError(f"{cls.__name__} with value {value} not found")

    def matches(self, event) -> bool:
        """Return whether the given object matches this control event.
        
        :param event: The object to check.
        :return: `True` when the provided object matches this event, `False` otherwise.
        """
        if isinstance(event, pygame.event.Event):
            return event.type == self.value
        elif isinstance(event, ControlEvent):
            return event == self
        elif isinstance(event, int):
            return event == self.value
        return False

class PlayerAction(Enum):
    """Describes the actions a player can perform during a game."""

    PLACE_MARK = 0
    STOP = 1
    QUIT = 2

    @classmethod
    def all(cls) -> Set['PlayerAction']:
        """Return all player actions.

        :return: The complete set of player actions.
        """
        return set(cls.__members__.values())

@dataclass(frozen=True)
class ActionMap:
    """Represent the mapping between input keys and a player action."""

    place_mark: int
    click_point: Vector2 = field(default_factory=Vector2)
    quit: int = pygame.K_ESCAPE
    name: str = 'custom'

    def to_key_map(self):
        """Convert the action map into a key-to-action dictionary.

        :return: The mapping from input identifiers to :class:`PlayerAction` values.
        """
        return {getattr(self, name): PlayerAction[name.upper()]
                for name in self.__annotations__ if name not in ('name', 'click_point')}

    @classmethod
    def click(cls) -> 'ActionMap':
        """Create an action map for a mouse click at the current cursor position.

        :return: A click-based action map using the current mouse position.
        """
        return cls(pygame.MOUSEBUTTONDOWN, click_point=Vector2(pygame.mouse.get_pos()), name="click")

def create_event(event: pygame.event.Event | LobbyEvent | ControlEvent, **kwargs) -> pygame.event.Event:
    """Create a pygame event from either a pygame event or a :class:`ControlEvent`.

    :param event: The source event or control event.
    :param kwargs: Additional payload values to attach to the event dictionary.
    :return: The constructed pygame event object.
    """
    if isinstance(event, (LobbyEvent, ControlEvent)):
        event = pygame.event.Event(event.value, **kwargs)
    elif isinstance(event, pygame.event.Event) and event.dict != kwargs:
        data = event.dict
        data.update(kwargs)
        event = pygame.event.Event(event.type, data)
    return event

def post_event(event: pygame.event.Event | LobbyEvent | ControlEvent, **kwargs) -> pygame.event.Event:
    """Create and post an event to the pygame queue.

    :param event: The event to convert and dispatch.
    :param kwargs: Extra data to include in the event payload.
    :return: The posted pygame event.
    """
    event = create_event(event, **kwargs)
    pygame.event.post(event)
    return event

class InputHandler:
    """Handler for input events."""

    INPUT_EVENTS = (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN)

    def create_event(self, event: pygame.event.Event | LobbyEvent | ControlEvent, **kwargs) -> pygame.event.Event:
        return create_event(event, **kwargs)

    def post_event(self, event: pygame.event.Event | LobbyEvent | ControlEvent, **kwargs) -> pygame.event.Event:
        return post_event(event, **kwargs)

    def mouse_clicked(self):
        """Handle a mouse-click input from the user."""
        pass

    def time_elapsed(self, dt: float):
        """Post the event :ref:`ControlEvent.TIME_ELAPSED` that a time interval has elapsed.

        :param dt: The elapsed time in milliseconds.
        """
        self.post_event(ControlEvent.TIME_ELAPSED, dt=dt)

    def handle_inputs(self, dt=None):
        """Handle the pending input events.

        :param dt: Optional elapsed time.
        """
        pass

class LobbyEventHandler:
    """Handler for lobby events."""

    LOBBY_EVENTS = tuple(LobbyEvent.all_types())

    def handle_events(self):
        """Handle pygame lobby events present in the event queue."""
        for event in pygame.event.get(self.LOBBY_EVENTS):
            if LobbyEvent.CREATE_GAME.matches(event):
                self.on_create_game(**event.dict)
            elif LobbyEvent.DELETE_GAME.matches(event):
                self.on_delete_game(**event.dict)
            elif LobbyEvent.JOIN_GAME.matches(event):
                self.on_join_game(**event.dict)
            elif LobbyEvent.REQUEST_JOINABLE_GAME_IDS.matches(event):
                self.on_request_joinable_game_ids(**event.dict)

    def create_event(self, event: pygame.event.Event | LobbyEvent, **kwargs) -> pygame.event.Event:
        """Create a pygame event object from a lobby event or a pygame event.

        :param event: The pygame event instance or a :class:`LobbyEvent`.
        :param kwargs: Additional data to attach to the event payload.
        :return: The constructed event.
        """
        return create_event(event, **kwargs)

    def post_event(self, event: pygame.event.Event | LobbyEvent, **kwargs) -> pygame.event.Event:
        """Post a pygame event or a :class:`LobbyEvent` into the pygame queue.

        :param event: The event to post.
        :param kwargs: Extra payload values for the emitted event.
        :return: The posted event.
        """
        return post_event(event, **kwargs)

    def on_create_game(self, **kwargs):
        """Handle a request to create a new game from the lobby.

        :param kwargs: Additional game-creation arguments.
        """
        pass

    def on_delete_game(self, game_id: int):
        """Handle a request to delete an existing game from the lobby.

        :param game_id: The identifier of the game to delete.
        """
        pass

    def on_join_game(self, game_id: int, **kwargs):
        """Handle a request to join a specific game from the lobby.

        :param game_id: The identifier of the game to join.
        :param kwargs: Additional join-game arguments.
        """
        pass

    def on_request_joinable_game_ids(self, **kwargs):
        """Handle a request to list the games currently available for joining.

        :param kwargs: Additional arguments.
        """
        pass

class EventHandler:
    """Create an event handler bound to a specific game instance.

    :param tic_tac_toe: The :class:`TicTacToe` instance.
    """

    GAME_EVENTS = tuple(ControlEvent.all_types())

    def __init__(self, tic_tac_toe: TicTacToe):
        self._tic_tac_toe = tic_tac_toe

    def handle_events(self):
        """Process every queued :class:`ControlEvent`."""
        for event in pygame.event.get(self.GAME_EVENTS):
            if ControlEvent.PLAYER_CREATE_GAME.matches(event):
                self.on_player_create_game(**event.dict)
            elif ControlEvent.PLAYER_JOIN_GAME.matches(event):
                self.on_player_join_game(**event.dict)
            elif ControlEvent.PLAYER_JOIN.matches(event):
                self.on_player_join(self._tic_tac_toe, **event.dict)
            elif ControlEvent.PLAYER_LEAVE.matches(event):
                self.on_player_leave(self._tic_tac_toe, **event.dict)
            elif ControlEvent.GAME_START.matches(event):
                self.on_game_start(self._tic_tac_toe)
            elif ControlEvent.GAME_OVER.matches(event):
                self.on_game_over(self._tic_tac_toe, **event.dict)
            elif ControlEvent.MARK_PLACED.matches(event):
                self.on_mark_placed(self._tic_tac_toe, **event.dict)
            elif ControlEvent.CHANGE_TURN.matches(event):
                self.on_change_turn(self._tic_tac_toe)
            elif ControlEvent.TIME_ELAPSED.matches(event):
                self.on_time_elapsed(self._tic_tac_toe, **event.dict)

    def on_player_create_game(self, symbol: Symbol):
        """Handle creation of a new game from the lobby.

        :param symbol: The symbol chosen by the player.
        """
        pass

    def on_player_join_game(self, symbol: Symbol, game_id: int):
        """Handle a request to join an existing game from the lobby.

        :param symbol: The symbol chosen by the joining player.
        :param game_id: The identifier of the game to join.
        """
        pass

    def on_player_join(self, tic_tac_toe: TicTacToe, symbol: Symbol, **kwargs):
        """Handle a player joining an active game session.

        :param tic_tac_toe: The :class:`TicTacToe` instance.
        :param symbol: The symbol chosen by the player.
        :param kwargs: Additional player-join arguments.
        """
        pass

    def on_player_leave(self, tic_tac_toe: TicTacToe, symbol: Symbol):
        """Handle a player leaving the game.

        :param tic_tac_toe: The current :class:`TicTacToe` instance.
        :param symbol: The symbol of the leaving player.
        """
        pass

    def on_game_start(self, tic_tac_toe: TicTacToe):
        """Start of the game.

        :param tic_tac_toe: The :class:`TicTacToe` instance to start.
        """
        pass

    def on_game_over(self, tic_tac_toe: TicTacToe, **kwargs):
        """Handle the end of the game.

        :param tic_tac_toe: The :class:`TicTacToe` instance that ended.
        :param kwargs: Additional end-of-game arguments.
        """
        pass

    def on_mark_placed(self, tic_tac_toe: TicTacToe, cell: Cell, symbol: Symbol):
        """Handle a mark placement on the grid.

        :param tic_tac_toe: The :class:`TicTacToe` instance.
        :param cell: The cell where the mark should be placed.
        :param symbol: The symbol of the mark to be placed.
        """
        pass

    def on_change_turn(self, tic_tac_toe: TicTacToe):
        """Change the turn of the game.

        :param tic_tac_toe: The :class:`TicTacToe` instance.
        """
        pass

    def on_time_elapsed(self, tic_tac_toe: TicTacToe, dt: float):
        """Handle time progression during a game.

        :param tic_tac_toe: The :class:`TicTacToe` instance.
        :param dt: The elapsed time in milliseconds.
        """
        pass
