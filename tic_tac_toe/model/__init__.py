import random
from .grid import *
from .game_object import *
from ..utils import *

class TicTacToe(Sized):
    def __init__(self, size, dim=Settings.dim, players=[]):
        self.size = Vector2(size)
        self.config = Config(self.size.x/dim, self.size.y/dim)
        self.players = players
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
        assert isinstance(player, Player), "The player provided has not a valid symbol"
        assert list(filter(lambda p: p == player, self.players)).__len__() == 0, "The player's already joined the game"
        self._players.append(player)
        logger.debug(f"Add {player}")

    def player(self, player: Player):
        if player not in self._players:
            raise ValueError(f"No such a player with {player.symbol}")
        return list(filter(lambda p: p == player, self._players))[0]

    def remove_player_by_symbol(self, symbol: Symbol):
        if list(filter(lambda p: p.symbol == symbol, self._players)).__len__() == 0:
            raise ValueError(f"No such player with {symbol}")
        self.players = list(filter(lambda p: p.symbol != symbol, self._players))
        logger.debug(f"Removed player from {self} with {symbol}")

    def is_player_lobby_full(self) -> bool:
        return self.players.__len__() == Settings.lobby_size

    @property
    def marks(self) -> list[Mark]:
        return sorted(self._marks, key=lambda m: (m.cell.x, m.cell.y))
    
    @marks.setter
    def marks(self, marks) -> list[Mark]:
        self._marks = []
        for mark in marks:
            assert isinstance(mark, Mark), f"Invalid mark: {mark}"
            self._marks.append(mark)


    def place_mark(self, mark: Mark) -> bool:
        if list(map(lambda m: m.cell, self.marks)).__contains__(mark.cell):
            logger.debug(f"{mark.cell} is already marked.")
            return False
        else:
            self._marks.append(mark)
            logger.debug(f"Added {mark} to {self} on {mark.cell}")
            return True

    def has_mark(self, cell: Cell) -> bool:
        assert cell is not None, "Cell not provided, but necessary"
        return list(filter(lambda m: m.cell == cell, self.marks)).__len__() > 0

    def get_mark(self, cell: Cell) -> Mark:
        if self.has_mark(cell):
            return list(filter(lambda m: m.cell == cell, self.marks)).__getitem__(0)
        else:
            raise ValueError(f"{cell} is not marked")

    def remove_mark(self, cell: Cell):
        self._marks.remove(self.get_mark(cell))
        logger.debug(f"Removed mark on {cell} from {self}")

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

    def check_game_end(self) -> Player:
        def has_won(player: Player) -> bool:
            cells_marked = list(map(lambda m: m.cell, self.get_noughts() if player.symbol.is_nought else self.get_crosses()))
            for row in self._get_rows():
                if len(cells_marked).__ge__(self.grid.dim) and all(list(map(lambda cell: cell in cells_marked, row))):
                    return True
            for col in self._get_columns():
                if len(cells_marked).__ge__(self.grid.dim) and all(list(map(lambda cell: cell in cells_marked, col))):
                    return True
            return len(cells_marked).__ge__(self.grid.dim) and \
                (all(list(map(lambda cell: cell in cells_marked, self._get_diagonal()))) or \
                all(list(map(lambda cell: cell in cells_marked, self._get_antidiagonal()))))

        for player in self.players:
            if has_won(player):
                logger.debug(f"The {player} has won")
                return player
        logger.debug(f"Game not ended")
        return None

    def reset_grid(self):
        self.marks = list()
        self.grid = Grid(self.grid.dim)
        logger.debug(f"Reset grid")

    def update(self, delta_time: float):
        self.updates += 1
        self.time += delta_time
        logger.debug(f"Update {self.updates} (time: {self.time})")

    def get_turn_player(self) -> Player:
        return list(filter(lambda p: p.symbol == self.turn, self.players))[0]

    def change_turn(self):
        self.turn = Symbol.CROSS if self.turn.is_nought else Symbol.NOUGHT
        logger.debug(f"Change turn. Now the player '{self.turn.value}' is in turn")

    def override(self, other: 'TicTacToe'):
        if self == other:
            return
        logger.debug(f"Overriding TicTacToe status")
        self.size = other.size
        self.config = other.config
        self.updates = other.updates
        self.time = other.time
        self.turn = other.turn
        my_marks = self.marks
        other_marks = other.marks
        for other_mark in other_marks:
            if not my_marks.__contains__(other_mark):
                self.place_mark(other_mark)
        for mark in my_marks:
            if not other_marks.__contains__(mark):
                self.remove_mark(mark.cell)
            else:
                self.get_mark(mark.cell).override(other.get_mark(mark.cell))
        my_players = self.players
        other_players = other.players
        for other_player in other_players:
            if not my_players.__contains__(other_player):
                self.add_player(other_player)
        for player in my_players:
            if not other_players.__contains__(player):
                self.remove_player_by_symbol(player.symbol)

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
