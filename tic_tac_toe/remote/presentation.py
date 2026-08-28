from typing import Any, Iterable
from pygame.event import Event
from tic_tac_toe.model.grid import *
from tic_tac_toe.model.game_object import *
from tic_tac_toe.model import *
from tic_tac_toe.controller import ControlEvent, LobbyEvent
from tic_tac_toe.utils import Config
import json

_DEBUG = False

class Serializer:
    """Serializer from various object types to JSON format."""

    primitives = [int, float, str, bool]
    containers = [list, tuple]

    def serialize(self, obj: Any) -> str:
        """Serialize an object into a JSON representation.

        :param obj: The object to serialize.
        :return: The JSON text representing the object.
        :raise NotImplementedError: If the object's type is unsupported.
        """
        return json.dumps(self._serialize(obj), indent=2 if _DEBUG else None)

    def _serialize(self, obj: Any) -> (Any | Dict | Iterable):
        if any(isinstance(obj, primitive) for primitive in self.primitives):
            return self._serialize_primitive(obj)
        elif isinstance(obj, dict):
            return self._serialize_dict(obj)
        elif any(isinstance(obj, container) for container in self.containers):
            return self._serialize_iterable(obj)
        else:
            return self._serialize_any(obj)

    def _serialize_iterable(self, obj: Iterable) -> Iterable:
        return [self._serialize(item) for item in obj]

    def _serialize_dict(self, obj: Dict) -> Dict:
        return {key: self._serialize(value) for key, value in obj.items()}

    def _serialize_primitive(self, obj: Any) -> Any:
        return obj

    def _serialize_any(self, obj: Any) -> Any:
        for klass in type(obj).mro():
            method_name = f"_serialize_{klass.__name__.lower()}"
            if hasattr(self, method_name):
                return getattr(self, method_name)(obj)
        raise NotImplementedError(f"Serialization for {type(obj).__name__} is not implemented")

    def _to_dict(self, obj: Any, *attributes) -> Dict:
        dict = {name : self._serialize(getattr(obj, name)) for name in attributes}
        dict["$type"] = type(obj).__name__
        return dict

    def _serialize_controlevent(self, control_event: ControlEvent) -> Dict:
        return self._to_dict(control_event, "name")
    
    def _serialize_lobbyevent(self, lobby_event: LobbyEvent) -> Dict:
        return self._to_dict(lobby_event, "name")

    def _serialize_event(self, event: Event) -> Dict:
        obj = self._to_dict(event, "type", "dict")
        if ControlEvent.is_control_event(event):
            obj["type"] = self._serialize(ControlEvent.by_value(event.type))
        elif LobbyEvent.is_lobby_event(event):
            obj["type"] = self._serialize(LobbyEvent.by_value(event.type))
        return obj

    def _serialize_gameobject(self, obj: GameObject) -> Dict:
        return self._to_dict(obj, "size", "position", "name")

    def _serialize_cell(self, cell: Cell) -> Dict:
        return self._to_dict(cell, "x", "y")

    def _serialize_symbol(self, symbol: Symbol) -> Dict:
        return self._to_dict(symbol, "name")

    def _serialize_player(self, player: Player) -> Dict:
        return self._to_dict(player, "symbol")

    def _serialize_mark(self, mark: Mark) -> Dict:
        return self._to_dict(mark, "size", "position", "name", "cell", "symbol")
    
    def _serialize_grid(self, grid: Grid) -> Dict:
        return self._to_dict(grid, "dim", "cells")

    def _serialize_vector2(self, vector: Vector2) -> Dict:
        return self._to_dict(vector, "x", "y")

    def _serialize_config(self, config: Config) -> Dict:
        return self._to_dict(config, 'cell_width_size', 'cell_height_size')

    def _serialize_tictactoe(self, tic_tac_toe: TicTacToe) -> Dict:
        return self._to_dict(tic_tac_toe, 'players', 'marks', 'grid', 'turn', 'config', 'size', 'time', 'updates')

class Deserializer:
    """Deserializer from JSON format to various object types."""

    def deserialize(self, input: str) -> Any:
        """Deserialize a JSON representation into its corresponding object type.

        :param input: The JSON text to deserialize.
        :return: The reconstructed object or primitive value.
        :raise NotImplementedError: If the JSON contains an unsupported type.
        """
        return self._deserialize(json.loads(input))

    def _deserialize(self, obj: Any) -> Any:
        if isinstance(obj, dict):
            if "$type" in obj:
                return self._deserialize_any(obj)
            else:
                return {key: self._deserialize(value) for key, value in obj.items()}
        if isinstance(obj, list):
            return [self._deserialize(item) for item in obj]
        return obj

    def _deserialize_any(self, obj: Any) -> Any:
        type_name = obj["$type"]
        method_name = f"_deserialize_{type_name.lower()}"
        if hasattr(self, method_name):
            return getattr(self, method_name)(obj)
        raise NotImplementedError(f"Deserialization for {type_name} is not implemented")

    def _from_dict(self, obj: Dict, *attributes) -> List:
        return [self._deserialize(obj[name]) for name in attributes]

    def _deserialize_controlevent(self, obj: Any) -> ControlEvent:
        return ControlEvent[obj["name"]]

    def _deserialize_lobbyevent(self, obj: Any) -> LobbyEvent:
        return LobbyEvent[obj["name"]]

    def _deserialize_event(self, obj: Any) -> Event:
        fields = self._from_dict(obj, "type", "dict")
        if isinstance(fields[0], ControlEvent):
            fields[0] = fields[0].value
        elif isinstance(fields[0], LobbyEvent):
            fields[0] = fields[0].value
        return Event(*fields)

    def _deserialize_vector2(self, obj: Any) -> Vector2:
        return Vector2(*self._from_dict(obj, "x", "y"))
    
    def _deserialize_cell(self, obj: Any) -> Cell:
        return Cell(*self._from_dict(obj, "x", "y"))

    def _deserialize_symbol(self, obj: Any) -> Symbol:
        return Symbol[obj["name"]]

    def _deserialize_player(self, obj: Any) -> Player:
        return Player(*self._from_dict(obj, "symbol"))

    def _deserialize_mark(self, obj: Any) -> Mark:
        return Mark(*self._from_dict(obj, "cell", "symbol", "size", "position", "name"))
    
    def _deserialize_grid(self, obj: Any) -> Grid:
        return Grid(*self._from_dict(obj, "dim"))

    def _deserialize_config(self, obj: Any) -> Config:
        return Config(*self._from_dict(obj, 'cell_width_size', 'cell_height_size'))

    def _deserialize_tictactoe(self, obj: Any) -> TicTacToe:
        tic_tac_toe = TicTacToe(*self._from_dict(obj, 'size'))
        tic_tac_toe.players = self._deserialize(obj['players'])
        tic_tac_toe.marks = self._deserialize(obj['marks'])
        tic_tac_toe.turn = self._deserialize(obj['turn'])
        tic_tac_toe.grid = self._deserialize(obj['grid'])
        tic_tac_toe.config = self._deserialize(obj['config'])
        tic_tac_toe.time = self._deserialize(obj['time'])
        tic_tac_toe.updates = self._deserialize(obj['updates'])
        return tic_tac_toe

DEFAULT_SERIALIZER = Serializer()
DEFAULT_DESERIALIZER = Deserializer()

def serialize(obj: Any, serializer: Serializer=DEFAULT_SERIALIZER) -> str:
    """Serialize an object using the supplied serializer.

    :param obj: The object to serialize.
    :param serializer: The :class:`Serializer` implementation to use.
    :return: The JSON text representation of the object.
    """
    return serializer.serialize(obj)


def deserialize(input: str, deserializer: Deserializer=DEFAULT_DESERIALIZER) -> Any:
    """Deserialize JSON text using the supplied deserializer.

    :param input: The JSON text to deserialize.
    :param deserializer: The :class:`Deserializer` implementation to use.
    :return: The reconstructed object or primitive value.
    """
    return deserializer.deserialize(input)
