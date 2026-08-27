from typing import List
from pygame.math import Vector2
from enum import Enum
from ..log import logger
from dataclasses import dataclass

class Sized:
    """Provide width and height properties for objects with a size."""

    @property
    def width(self) -> float:
        """Return the horizontal size of the object.

        :return: Object width.
        """

        return self.size.x # type: ignore[attr-defined]

    @property
    def height(self) -> float:
        """Return the vertical size of the object.

        :return: Object height.
        """

        return self.size.y # type: ignore[attr-defined]

class Positioned:
    """Provide coordinates properties for objects with a position."""

    @property
    def x(self) -> float:
        """Return the horizontal position of the object.

        :return: Object x-coordinate.
        """

        return self.position.x # type: ignore[attr-defined]

    @property
    def y(self) -> float:
        """Return the vertical position of the object.

        :return: Object y-coordinate.
        """

        return self.position.y # type: ignore[attr-defined]

class GameObject(Sized, Positioned):
    """Represent an object in the game view with size and position.

    :param size: The size of the object.
    :param position: The optional position of the object.
    :param name: The optional object name.
    """

    def __init__(self, size: Vector2, position: Vector2=None, name: str=None):
        self._size = Vector2(size)
        self._position = Vector2(position) if position is not None else Vector2()
        self.name = name or self.__class__.__name__.lower()
        self.logger = logger("GameObject")

    def __eq__(self, other: 'GameObject'):
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
        """Return the object size.

        :return: The size as a vector.
        """

        return self._size
    
    @size.setter
    def size(self, value: Vector2):
        """Set the object size.

        :param value: The new size as a vector.
        """

        old_value = self._size
        self._size = Vector2(value)
        if old_value is not None and old_value != self._size:
            self.logger.debug(f"{self} resized: {old_value} -> {self._size}")

    @property
    def position(self) -> Vector2:
        """Return the object position.

        :return: The position as a vector.
        """

        return self._position
    
    @position.setter
    def position(self, value: Vector2):
        """Set the object position.

        :param value: The new position as a vector.
        """

        old_value = self._position
        self._position = Vector2(value)
        if old_value is not None and old_value != self._position:
            self.logger.debug(f"{self} moves: {old_value} -> {self._position}")

    def override(self, other: 'GameObject'):
        """Override the current object with another valid :class:`GameObject`.

        :param other: The object from which to override.
        """

        assert isinstance(other, type(self)) and other.name == self.name, f"Invalid override: {other} -> {self}"
        self.size = other.size
        self.position = other.position

class Symbol(Enum):
    """The symbols that players can place on the grid."""

    NOUGHT = "O"
    CROSS = "X"

    def __repr__(self):
        return f"<{type(self).__name__}.{self.name}>"

    @property
    def is_nought(self) -> bool:
        """Return whether this symbol is a nought.

        :return: `True` if the symbol is a nought, `False` otherwise.
        """

        return self.value == "O"

    @property
    def is_cross(self) -> bool:
        """Return whether this symbol is a cross.

        :return: `True` if the symbol is a cross, `False` otherwise.
        """

        return self.value == "X"

    @classmethod
    def values(cls) -> List['Symbol']:
        """Return all available symbols.

        :return: The list of all symbols.
        """

        return list(cls.__members__.values())

@dataclass
class Player:
    """Represent a player identified by a :class:`Symbol`.

    :param symbol: The symbol assigned to the player.
    """

    symbol: Symbol

    def __eq__(self, other: 'Player'):
        return isinstance(other, type(self)) and self.symbol == other.symbol

    def __hash__(self):
        return hash((self.symbol))
    
    def __repr__(self):
        return f'<{type(self).__name__}(id={id(self)}, symbol={self.symbol})>'

class Mark(GameObject):
    """Represent a mark placed in a grid cell with a specific symbol.

    :param cell: The cell where the mark will be placed.
    :param symbol: The symbol of the mark.
    :param size: The size of the mark.
    :param position: The position of the mark.
    :param name: The optional mark name.
    """
    from .grid import Cell

    def __init__(self, cell: Cell, symbol: Symbol, size: Vector2=Vector2(0), position: Vector2=None, name: str=None):
        super().__init__(size, position, name or "mark_" + symbol.name.lower())
        self.cell = cell
        self.symbol = symbol

    def __eq__(self, other: 'Mark'):
        return super().__eq__(other) and self.cell == other.cell and self.symbol == other.symbol

    def __hash__(self):
        return hash((super().__hash__(), self.cell, self.symbol))

    def __repr__(self):
        return super().__repr__().replace(')>', f", cell={self.cell}, symbol={self.symbol})>")

    def override(self, other: GameObject):
        super().override(other)
        self.cell = other.cell # type: ignore[attr-defined]
        self.symbol = other.symbol # type: ignore[attr-defined]
