from ..model.game_object import Symbol, Mark

class MarkUtils:
    @property
    def symbols(self) -> dict:
        return {key: value for key, value in map(lambda s: (s.name, s.value), Symbol.values())}

    def decompose(self, marks: list[Mark]) -> list['MarkView']:
            return list(map(lambda m: MarkView(m.symbol.value, (m.cell.x, m.cell.y), (m.position.x, m.position.y)), marks))

class MarkView:
    def __init__(self, symbol: str, cell: tuple, position: tuple):
        self.__symbol = symbol
        self.__cell = cell
        self.__position = position

    @property
    def is_nought(self) -> bool:
        return self.__symbol == Symbol.NOUGHT.value

    @property
    def symbol(self) -> str:
        return self.__symbol

    @property
    def cell(self) -> tuple:
        return self.__cell

    @property
    def position(self) -> tuple:
        return self.__position
