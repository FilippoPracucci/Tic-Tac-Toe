import random
from .grid import *
from .game_object import *
from ..utils import *

class TicTacToe(Sized):
    def __init__(self, size, dim=Settings.dim):
        self.size = Vector2(size)
        self.config = Config(self.size.x/dim, self.size.y/dim)
        self.players = []
        self.grid = Grid(dim) if dim is not None else Grid()
        self.marks = list()
        self.turn: Symbol = Symbol.CROSS
        self.updates = 0
        self.time = 0

    def __eq__(self, value):
        return isinstance(value, TicTacToe) and \
            self.size == value.size and \
            self.config == value.config and \
            self.grid == value.grid and \
            self.players == value.players and \
            self.marks == value.marks and \
            self.turn == value.turn and \
            self.updates == value.updates and \
            self.time == value.time

    def __hash__(self):
        return hash((self.size, self.config, self.grid, tuple(self.players), tuple(self.marks), self.turn, self.updates, self.time))

    def __repr__(self):
        return (f'<{type(self).__name__}('
                f'id={id(self)}, '
                f'size={self.size}, '
                f'time={self.time}, '
                f'updates={self.updates}, '
                f'config={self.config}, '
                f'players={self.players}, '
                f'marks={self.marks}, '
                f'turn={repr(self.turn)}'
                f')>')

    @property
    def players(self) -> list[Player]:
        return list(self._players)
    
    @players.setter
    def players(self, players: list[Player]) -> list[Player]:
        self._players = []
        for player in players:
            assert isinstance(player, Player), f"Invalid symbol for a player: {player.symbol}"
            self._players.append(player)

    def add_player(self, player: Player):
        logger.debug(f"Add player {player}")
        assert isinstance(player, Player), "The player provided has not a valid symbol"
        #assert list(filter(lambda p: p == player, self.players)).__len__() == 0
        self._players.append(player)

    def player(self, player: Player):
        if player not in self._players:
            raise ValueError(f"No such a player: {player.symbol}")
        return list(filter(lambda p: p == player, self._players))[0]

    def remove_player(self, symbol: Symbol):
        if list(filter(lambda p: p.symbol == symbol, self._players)).__len__() == 0:
            raise ValueError(f"No such player with symbol {symbol}")
        self.players = list(filter(lambda p: p.symbol != symbol, self._players))
        logger.debug(f"Removed player from {self} with symbol {symbol}")

    @property
    def marks(self) -> list[Mark]:
        return list(self._marks)
    
    @marks.setter
    def marks(self, marks) -> list[Mark]:
        self._marks = []
        for mark in marks:
            assert isinstance(mark, Mark), f"Invalid mark: {mark}"
            self._marks.append(mark)


    def place_mark(self, mark: Mark) -> bool:
        if list(map(lambda m: m.cell, self.marks)).__contains__(mark.cell):
            logger.debug(f"Cell {(mark.cell.x, mark.cell.y)} is already marked.")
            return False
        else:
            self._marks.append(mark)
            logger.debug(f"Added mark {mark} to {self} on cell {mark.cell}")
            return True

    def has_mark(self, cell: Cell) -> bool:
        assert cell is not None, "Cell not provided, but necessary"
        return list(filter(lambda m: m.cell == cell, self.marks)).__len__() > 0

    def get_mark(self, cell: Cell) -> Mark:
        if self.has_mark(cell):
            return list(filter(lambda m: m.cell == cell, self.marks)).__getitem__(0)
        else:
            raise ValueError(f"Cell {cell} is not marked")

    def remove_mark(self, cell: Cell):
        self._marks.remove(self.get_mark(cell))

    def remove_random_mark(self):
        turn_marks = self.get_crosses() if self.turn.is_cross else self.get_noughts()
        if turn_marks.__len__() >= self.grid.dim:
            r = random.randint(0, turn_marks.__len__() - 1)
            mark = turn_marks.__getitem__(r)
            self.remove_mark(mark.cell)

    def get_noughts(self) -> list[Mark]:
        return list(filter(lambda m: m.symbol is Symbol.NOUGHT, self.marks))

    def get_crosses(self) -> list[Mark]:
        return list(filter(lambda m: m.symbol is Symbol.CROSS, self.marks))
    
    def end_turn(self) -> bool:
        if self.has_won(self.turn):
            return True
        self.change_turn()
        self.remove_random_mark()

    def has_won(self, player: Symbol) -> bool:
        cells_marked = list(map(lambda m: m.cell, self.get_noughts() if player.is_nought else self.get_crosses()))
        for row in self._get_rows():
            if len(cells_marked).__ge__(self.grid.dim) and all(list(map(lambda cell: cell in cells_marked, row))):
                return True
        for col in self._get_columns():
            if len(cells_marked).__ge__(self.grid.dim) and all(list(map(lambda cell: cell in cells_marked, col))):
                return True
        return len(cells_marked).__ge__(self.grid.dim) and \
            (all(list(map(lambda cell: cell in cells_marked, self._get_diagonal()))) or \
             all(list(map(lambda cell: cell in cells_marked, self._get_antidiagonal()))))

    def reset_grid(self):
        self.marks = list()
        self.grid = Grid(self.grid.dim)

    def update(self, delta_time: float):
        self.updates += 1
        self.time += delta_time
        logger.debug(f"Update {self.updates} (time: {self.time})")

    def change_turn(self):
        self.turn = Symbol.CROSS if self.turn.is_nought else Symbol.NOUGHT

    def override(self, other: 'TicTacToe'):
        logger.debug(f"Overriding TicTacToe status")
        if self is other:
            return
        self.marks = other.marks
        """ self.size = other.size
        self.config = other.config
        self.updates = other.updates
        self.time = other.time
        my_marks = set((mark.cell for mark in self.marks))
        other_marks = set((mark.cell for mark in other.marks))
        added = other_marks - my_marks
        added = {m: other._marks[m] for m in added}
        removed = my_marks - other_marks
        removed = {m: self._marks[m] for m in removed}
        common = my_marks & other_marks
        common = {m: other._marks[m] for m in common}
        for _, mark in added.items():
            self.place_mark(mark)
        for cell, _ in removed.items():
            self.remove_mark(cell)
        for cell, mark in common.items():
            self.get_mark(cell).override(other.get_mark(cell))
        print(f"ADDED: {added} - REMOVED: {removed}")
        return added, removed """

    def _get_diagonal(self) -> list[Cell]:
        return list(filter(lambda c: c.x == c.y, self.grid.cells))

    def _get_antidiagonal(self) -> list[Cell]:
        reversed_cells = self._get_rows().copy()
        return [reversed_cells[i][-(i+1)] for i in range(len(reversed_cells))]

    def _get_columns(self) -> list[list[Cell]]:
        res = list()
        for i in range(self.grid.dim):
            col = list(filter(lambda c: c.x == i, self.grid.cells))
            res.append(col)
        return res

    def _get_rows(self) -> list[list[Cell]]:
        res = list()
        for j in range(self.grid.dim):
            row = list(filter(lambda c: c.y == j, self.grid.cells))
            res.append(row)
        return res
