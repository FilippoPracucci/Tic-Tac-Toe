import pygame
from ..model import *
from dataclasses import dataclass, field
from enum import Enum
from tic_tac_toe.model import Symbol
from typing import Set

class LobbyEvent(Enum):
    CREATE_GAME = pygame.event.custom_type()
    DELETE_GAME = pygame.event.custom_type()
    JOIN_GAME = pygame.event.custom_type()

    @classmethod
    def all(cls) -> Set['LobbyEvent']:
        return set(cls.__members__.values())

    @classmethod
    def all_types(cls) -> Set[int]:
        return {event.value for event in cls.all()}

    @classmethod
    def is_lobby_event(cls, event: pygame.event.Event) -> bool:
        return any(lobby_event.matches(event) for lobby_event in cls.all())

    @classmethod
    def by_value(cls, value: int) -> 'LobbyEvent':
        for lobby_event in cls.all():
            if lobby_event.value == value:
                return lobby_event
        raise KeyError(f"{cls.__name__} with value {value} not found")

    def matches(self, event) -> bool:
        if isinstance(event, pygame.event.Event):
            return event.type == self.value
        elif isinstance(event, LobbyEvent):
            return event == self
        elif isinstance(event, int):
            return event == self.value
        return False

class ControlEvent(Enum):
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
        return set(cls.__members__.values())

    @classmethod
    def all_types(cls) -> Set[int]:
        return {event.value for event in cls.all()}

    @classmethod
    def is_control_event(cls, event: pygame.event.Event) -> bool:
        return any(control_event.matches(event) for control_event in cls.all())

    @classmethod
    def by_value(cls, value: int) -> 'ControlEvent':
        for control_event in cls.all():
            if control_event.value == value:
                return control_event
        raise KeyError(f"{cls.__name__} with value {value} not found")

    def matches(self, event) -> bool:
        if isinstance(event, pygame.event.Event):
            return event.type == self.value
        elif isinstance(event, ControlEvent):
            return event == self
        elif isinstance(event, int):
            return event == self.value
        return False

class PlayerAction(Enum):
    PLACE_MARK = 0
    STOP = 1
    QUIT = 2

    @classmethod
    def all(cls) -> Set['PlayerAction']:
        return set(cls.__members__.values())

@dataclass(frozen=True)
class ActionMap:
    place_mark: int
    click_point: Vector2 = field(default_factory=Vector2)
    quit: int = pygame.K_ESCAPE
    name: str = 'custom'

    def to_key_map(self):
        return {getattr(self, name): PlayerAction[name.upper()]
                for name in self.__annotations__ if name not in ('name', 'click_point')}

    @classmethod
    def click(cls) -> 'ActionMap':
        return cls(pygame.MOUSEBUTTONDOWN, click_point=Vector2(pygame.mouse.get_pos()), name="click")

def create_event(event: pygame.event.Event | ControlEvent, **kwargs) -> pygame.event.Event:
    if isinstance(event, (LobbyEvent, ControlEvent)):
        event = pygame.event.Event(event.value, **kwargs)
    elif isinstance(event, pygame.event.Event) and event.dict != kwargs:
        data = event.dict
        data.update(kwargs)
        event = pygame.event.Event(event.type, data)
    return event

def post_event(event: pygame.event.Event | LobbyEvent | ControlEvent, **kwargs) -> pygame.event.Event:
    event = create_event(event, **kwargs)
    pygame.event.post(event)
    return event

class InputHandler:
    INPUT_EVENTS = (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN)

    def create_event(self, event: pygame.event.Event | LobbyEvent | ControlEvent, **kwargs) -> pygame.event.Event:
        return create_event(event, **kwargs)

    def post_event(self, event: pygame.event.Event | LobbyEvent | ControlEvent, **kwargs) -> pygame.event.Event:
        return post_event(event, **kwargs)

    def mouse_clicked(self):
        pass

    def time_elapsed(self, dt: float):
        self.post_event(ControlEvent.TIME_ELAPSED, dt=dt)

    def handle_inputs(self, dt=None):
        pass

class LobbyEventHandler:
    LOBBY_EVENTS = tuple(LobbyEvent.all_types())

    def handle_events(self):
        for event in pygame.event.get(self.LOBBY_EVENTS):
            if LobbyEvent.CREATE_GAME.matches(event):
                self.on_create_game(**event.dict)
            elif LobbyEvent.DELETE_GAME.matches(event):
                self.on_delete_game(**event.dict)
            elif LobbyEvent.JOIN_GAME.matches(event):
                self.on_join_game(**event.dict)

    def create_event(self, event: pygame.event.Event | LobbyEvent, **kwargs) -> pygame.event.Event:
        return create_event(event, **kwargs)

    def post_event(self, event: pygame.event.Event | LobbyEvent, **kwargs) -> pygame.event.Event:
        return post_event(event, **kwargs)

    def on_create_game(self, **kwargs):
        pass

    def on_delete_game(self, game_id: int):
        pass

    def on_join_game(self, game_id: int, **kwargs):
        pass

class EventHandler:
    GAME_EVENTS = tuple(ControlEvent.all_types())

    def __init__(self, tic_tac_toe: TicTacToe):
        self._tic_tac_toe = tic_tac_toe

    def handle_events(self):
        for event in pygame.event.get(self.GAME_EVENTS):
            if ControlEvent.PLAYER_CREATE_GAME.matches(event):
                self.on_player_create_game()
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

    def on_player_create_game(self):
        pass

    def on_player_join_game(self, game_id: int):
        pass

    def on_player_join(self, tic_tac_toe: TicTacToe, symbol: Symbol, **kwargs):
        pass

    def on_player_leave(self, tic_tac_toe: TicTacToe, symbol: Symbol):
        pass

    def on_game_start(self, tic_tac_toe: TicTacToe):
        pass

    def on_game_over(self, tic_tac_toe: TicTacToe, symbol: Symbol):
        pass

    def on_mark_placed(self, tic_tac_toe: TicTacToe, cell: Cell, symbol: Symbol):
        pass

    def on_change_turn(self, tic_tac_toe: TicTacToe):
        pass

    def on_time_elapsed(self, tic_tac_toe: TicTacToe, dt: float):
        pass
