from pygame.math import Vector2
from ..log import logger

class Sized:

    @property
    def width(self) -> float:
        return self.size.x

    @property
    def height(self) -> float:
        return self.size.y

class Positioned:

    @property
    def x(self) -> float:
        return self.position.x

    @property
    def y(self) -> float:
        return self.position.y

class GameObject(Sized, Positioned):
    def __init__(self, size, position=None, name=None):
        self._size = size
        self._position = Vector2(position) if position is not None else Vector2()
        self.name = name or self.__class__.__name__.lower()

    def __eq__(self, other):
        return isinstance(other, type(self)) and \
            self.name == other.name and \
            self._size == other._size and \
            self._position == other._position

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
        self._size = value
        if old_value is not None and old_value != self._size:
            logger.debug(f"{self} resized: {old_value} -> {self._size}")

    @property
    def position(self) -> Vector2:
        return self._position
    
    @position.setter
    def position(self, value: Vector2):
        old_value = self._position
        self._position = value
        if old_value is not None and old_value != self._position:
            logger.debug(f"{self} moves: {old_value} -> {self._position}")

    def override(self, other: 'GameObject'):
        assert isinstance(other, type(self)) and other.name == self.name, f"Invalid override: {other} -> {self}"
        self.size = other.size
        self.position = other.position
