from pygame.event import Event
from tic_tac_toe.model.grid import *
from tic_tac_toe.model.game_object import *
from tic_tac_toe.model import *
from tic_tac_toe.controller import ControlEvent
from tic_tac_toe.utils import Config
import json

_DEBUG = False

class Serializer:
    primitives = [int, float, str, bool]
    containers = [list, tuple]

    def serialize(self, obj) -> str:
        return json.dumps(self._serialize(obj), indent=2 if _DEBUG else None)

    def _serialize(self, obj):
        if any(isinstance(obj, primitive) for primitive in self.primitives):
            return self._serialize_primitive(obj)
        elif isinstance(obj, dict):
            return self._serialize_dict(obj)
        elif any(isinstance(obj, container) for container in self.containers):
            return self._serialize_iterable(obj)
        else:
            return self._serialize_any(obj)

    def _serialize_iterable(self, obj):
        return [self._serialize(item) for item in obj]

    def _serialize_dict(self, obj):
        return {key: self._serialize(value) for key, value in obj.items()}

    def _serialize_primitive(self, obj):
        return obj

    def _serialize_any(self, obj):
        for klass in type(obj).mro():
            method_name = f"_serialize_{klass.__name__.lower()}"
            if hasattr(self, method_name):
                return getattr(self, method_name)(obj)
        raise NotImplementedError(f"Serialization for {type(obj).__name__} is not implemented")

    def _to_dict(self, obj, *attributes):
        dict = {name : self._serialize(getattr(obj, name)) for name in attributes}
        dict["$type"] = type(obj).__name__
        return dict

    def _serialize_controlevent(self, control_event: ControlEvent):
        return self._to_dict(control_event, "name")

    def _serialize_event(self, event: Event):
        obj = self._to_dict(event, "type", "dict")
        if ControlEvent.is_control_event(event):
            obj["type"] = self._serialize(ControlEvent.by_value(event.type))
        return obj

    def _serialize_gameobject(self, obj: GameObject):
        return self._to_dict(obj, "size", "position", "name")

    def _serialize_cell(self, cell: Cell):
        return self._to_dict(cell, "x", "y")

    def _serialize_symbol(self, symbol: Symbol):
        return self._to_dict(symbol, "name")

    def _serialize_mark(self, mark: Mark):
        return self._to_dict(mark, "size", "position", "name", "cell", "symbol")
    
    def _serialize_grid(self, grid: Grid):
        return self._to_dict(grid, "dim", "cells")

    def _serialize_vector2(self, vector: Vector2):
        return self._to_dict(vector, "x", "y")

    def _serialize_config(self, config: Config):
        return self._to_dict(config, 'cell_width_size', 'cell_height_size')

    def _serialize_tictactoe(self, tic_tac_toe: TicTacToe):
        return self._to_dict(tic_tac_toe, 'marks', 'grid', 'turn', 'config', 'size', 'time', 'updates')

class Deserializer:
    def deserialize(self, input: str):
        return self._deserialize(json.loads(input))

    def _deserialize(self, obj):
        if isinstance(obj, dict):
            if "$type" in obj:
                return self._deserialize_any(obj)
            else:
                return {key: self._deserialize(value) for key, value in obj.items()}
        if isinstance(obj, list):
            return [self._deserialize(item) for item in obj]
        return obj

    def _deserialize_any(self, obj):
        type_name = obj["$type"]
        method_name = f"_deserialize_{type_name.lower()}"
        if hasattr(self, method_name):
            return getattr(self, method_name)(obj)
        raise NotImplementedError(f"Deserialization for {type_name} is not implemented")

    def _from_dict(self, obj: dict, *attributes):
        return [self._deserialize(obj[name]) for name in attributes]

    def _deserialize_controlevent(self, obj) -> ControlEvent:
        return ControlEvent[obj["name"]]

    def _deserialize_event(self, obj) -> Event:
        fields = self._from_dict(obj, "type", "dict")
        if isinstance(fields[0], ControlEvent):
            fields[0] = fields[0].value
        return Event(*fields)

    def _deserialize_vector2(self, obj) -> Vector2:
        return Vector2(*self._from_dict(obj, "x", "y"))
    
    def _deserialize_cell(self, obj) -> Cell:
        return Cell(*self._from_dict(obj, "x", "y"))

    def _deserialize_symbol(self, obj) -> Symbol:
        return Symbol[obj["name"]]

    def _deserialize_mark(self, obj) -> Mark:
        return Mark(*self._from_dict(obj, "cell", "symbol", "size", "position", "name"))
    
    def _deserialize_grid(self, obj) -> Grid:
        return Grid(*self._from_dict(obj, "dim"))

    def _deserialize_config(self, obj) -> Config:
        return Config(*self._from_dict(obj, 'cell_width_size', 'cell_height_size'))

    def _deserialize_tictactoe(self, obj) -> TicTacToe:
        tic_tac_toe = TicTacToe(*self._from_dict(obj, 'size'))
        tic_tac_toe.marks = self._deserialize(obj['marks'])
        tic_tac_toe.turn = self._deserialize(obj['turn'])
        tic_tac_toe.grid = self._deserialize(obj['grid'])
        tic_tac_toe.config = self._deserialize(obj['config'])
        tic_tac_toe.time = self._deserialize(obj['time'])
        tic_tac_toe.updates = self._deserialize(obj['updates'])
        return tic_tac_toe

DEFAULT_SERIALIZER = Serializer()
DEFAULT_DESERIALIZER = Deserializer()

def serialize(obj, serializer=DEFAULT_SERIALIZER):
    return serializer.serialize(obj)


def deserialize(input: str, deserializer=DEFAULT_DESERIALIZER):
    return deserializer.deserialize(input)
