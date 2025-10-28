from pygame.math import Vector2
from enum import Enum
from ..log import logger
from dataclasses import dataclass

class Sized:

    @property
    def width(self) -> float:
        return self.size.x # type: ignore[attr-defined]

    @property
    def height(self) -> float:
        return self.size.y # type: ignore[attr-defined]

class Positioned:

    @property
    def x(self) -> float:
        return self.position.x # type: ignore[attr-defined]

    @property
    def y(self) -> float:
        return self.position.y # type: ignore[attr-defined]

class GameObject(Sized, Positioned):
    def __init__(self, size, position=None, name=None):
        self._size = Vector2(size)
        self._position = Vector2(position) if position is not None else Vector2()
        self.name = name or self.__class__.__name__.lower()

    def __eq__(self, other):
        return isinstance(other, type(self)) and \
            self.name == other.name and \
            self.size == other.size and \
            self.position == other.position

    def __hash__(self):
        return hash((type(self), self.name, self.size, self.position))

    def __repr__(self):
        return f'<{type(self).__name__}(id={id(self)}, name={self.name}, size={self.size}, position={self.position})>'

    def __str__(self):
        return f'{self.name}#{id(self)}'
    
    @property
    def size(self) -> Vector2:
        return self._size
    
    @size.setter
    def size(self, value: Vector2):
        old_value = self._size
        self._size = Vector2(value)
        if old_value is not None and old_value != self._size:
            logger.debug(f"{self} resized: {old_value} -> {self._size}")

    @property
    def position(self) -> Vector2:
        return self._position
    
    @position.setter
    def position(self, value: Vector2):
        old_value = self._position
        self._position = Vector2(value)
        if old_value is not None and old_value != self._position:
            logger.debug(f"{self} moves: {old_value} -> {self._position}")

    def override(self, other: 'GameObject'):
        assert isinstance(other, type(self)) and other.name == self.name, f"Invalid override: {other} -> {self}"
        self.size = other.size
        self.position = other.position

class Symbol(Enum):
    NOUGHT = "O"
    CROSS = "X"

    def __repr__(self):
        return f"<{type(self).__name__}.{self.name}>"

    @property
    def is_nought(self) -> bool:
        return self.value == "O"

    @property
    def is_cross(self) -> bool:
        return self.value == "X"

    @classmethod
    def values(cls) -> list['Symbol']:
        return list(cls.__members__.values())

@dataclass
class Player:
    symbol: Symbol

    def __hash__(self):
        return hash((self.symbol))

class Mark(GameObject):
    from .grid import Cell

    def __init__(self, cell: Cell, symbol: Symbol, size=Vector2(0), position=None, name=None):
        super().__init__(size, position, name or "mark_" + symbol.name.lower())
        self.cell = cell
        self.symbol = symbol

    def __eq__(self, other):
        return super().__eq__(other) and self.cell == other.cell and self.symbol == other.symbol

    def __hash__(self):
        return hash((super().__hash__(), self.cell, self.symbol))

    def __repr__(self):
        return super().__repr__().replace(')>', f", cell={self.cell}, symbol={self.symbol})>")

    @property
    def is_nought(self) -> bool:
        return self.symbol == Symbol.NOUGHT
