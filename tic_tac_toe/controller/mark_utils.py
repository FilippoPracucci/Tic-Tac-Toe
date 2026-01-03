from ..model.game_object import Symbol, Mark
from typing import Dict, List, Tuple

class MarkUtils:
    @property
    def symbols(self) -> Dict:
        return {key: value for key, value in map(lambda s: (s.name, s.value), Symbol.values())}

    def decompose(self, marks: List[Mark]) -> List['MarkView']:
            return list(map(lambda m: MarkView(m.symbol.value, (m.cell.x, m.cell.y), (m.position.x, m.position.y)), marks))

class MarkView:
    def __init__(self, symbol: str, cell: Tuple, position: Tuple):
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
    def cell(self) -> Tuple:
        return self.__cell

    @property
    def position(self) -> Tuple:
        return self.__position
