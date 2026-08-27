import random
from .grid import *
from .game_object import *
from ..utils import *
from typing import List


class TicTacToe(Sized):
    """The state of a tic-tac-toe game.

    :param size: The window size in pixels as a `(width, height)` tuple.
    :param dim: The grid dimension.
    :param players: The initial players participating in the game.
    """

    def __init__(self, size, dim: int = Settings.dim, players: List[Player] = []):
        self.size = Vector2(size)
        self.config = Config(self.size.x / dim, self.size.y / dim)
        self.players = players
        self.grid = Grid(dim) if dim is not None else Grid()
        self.marks = list()
        self.turn: Symbol = Symbol.CROSS
        self.updates = 0
        self.time = 0
        self.logger = logger("TicTacToe")

    def __eq__(self, value: 'TicTacToe'):
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
    def players(self) -> List[Player]:
        """Return the players currently in the game.

        :return: The list of players.
        """
        return list(self._players)

    @players.setter
    def players(self, players: List[Player]) -> List[Player]:
        """Replace the current player list with a new one.

        :param players: The new player list.
        :return: The updated list of players.
        """
        self._players = []
        for player in players:
            assert isinstance(player, Player), f"Invalid symbol for a player: {player.symbol}"
            self._players.append(player)

    def add_player(self, player: Player):
        """Add a player to the game if its symbol is available.

        :param player: The player to add.
        """
        if list(filter(lambda p: p.symbol == player.symbol, self.players)):
            raise ValueError(f"A player with symbol '{player.symbol}' has already joined the game!")
        self._players.append(player)
        self.logger.debug(f"Add {player}")

    def player(self, player: Player) -> Player:
        """Find a player by identity.

        :param player: The player reference to match.
        :return: The matching player instance.
        """
        if player not in self._players:
            raise ValueError(f"No such a player with {player.symbol}")
        return list(filter(lambda p: p == player, self._players))[0]

    def remove_player_by_symbol(self, symbol: Symbol):
        """Remove a player using its symbol.

        :param symbol: The symbol of the player to remove.
        """
        if not list(filter(lambda p: p.symbol == symbol, self._players)):
            raise ValueError(f"No such player with {symbol}")
        self.players = list(filter(lambda p: p.symbol != symbol, self._players))
        self.logger.debug(f"Removed player from {self} with {symbol}")

    def is_player_lobby_full(self) -> bool:
        """Check whether the lobby has reached the maximum size.

        :return: `True` when the lobby is full; otherwise `False`.
        """
        return len(self.players) == Settings.lobby_size

    @property
    def marks(self) -> List[Mark]:
        """Return the marks sorted by their cell coordinates.

        :return: The list of marks in ascending order.
        """
        return sorted(self._marks, key=lambda m: (m.cell.x, m.cell.y))

    @marks.setter
    def marks(self, marks) -> List[Mark]:
        """Replace the current mark list with a new one.

        :param marks: The new mark list.
        :return: The updated list of marks.
        """
        self._marks = []
        for mark in marks:
            assert isinstance(mark, Mark), f"Invalid mark: {mark}"
            self._marks.append(mark)

    def place_mark(self, mark: Mark) -> bool:
        """Place a mark on an empty cell.

        :param mark: The mark to add.
        :return: `True` when the mark is placed successfully; `False` if the target cell is already occupied.
        """
        if list(map(lambda m: m.cell, self.marks)).__contains__(mark.cell):
            self.logger.debug(f"{mark.cell} is already marked.")
            return False
        else:
            self._marks.append(mark)
            self.logger.debug(f"Added {mark} to {self} on {mark.cell}")
            return True

    def has_mark(self, cell: Cell) -> bool:
        """Check whether a cell already contains a mark.

        :param cell: The cell to inspect.
        :return: `True` if the cell is occupied; otherwise `False`.
        """
        assert cell is not None, "Cell not provided, but necessary"
        return list(filter(lambda m: m.cell == cell, self.marks))

    def get_mark(self, cell: Cell) -> Mark:
        """Retrieve the mark placed on a specific cell.

        :param cell: The cell to inspect.
        :return: The mark placed in the given cell.
        :raise: `ValueError` if the cell is not marked.
        """
        if self.has_mark(cell):
            return list(filter(lambda m: m.cell == cell, self.marks)).pop()
        else:
            raise ValueError(f"{cell} is not marked")

    def remove_mark(self, cell: Cell):
        """Remove the mark placed on a specific cell.

        :param cell: The cell whose mark should be removed.
        """
        self._marks.remove(self.get_mark(cell))
        self.logger.debug(f"Removed mark on {cell} from {self}")

    def remove_random_mark(self):
        """Remove a random mark owned by the active player."""
        turn_marks = self.get_crosses() if self.turn.is_cross else self.get_noughts()
        if len(turn_marks) >= self.grid.dim:
            r = random.randint(0, len(turn_marks) - 1)
            mark = turn_marks.__getitem__(r)
            self.remove_mark(mark.cell)

    def get_noughts(self) -> List[Mark]:
        """Return all marks belonging to the nought player.

        :return: The list of nought marks.
        """
        return list(filter(lambda m: m.symbol is Symbol.NOUGHT, self.marks))

    def get_crosses(self) -> List[Mark]:
        """Return all marks belonging to the cross player.

        :return: The list of cross marks.
        """
        return list(filter(lambda m: m.symbol is Symbol.CROSS, self.marks))

    def check_game_end(self) -> Player:
        """Check whether one of the players has completed a winning line.

        :return: The winning player, or `None` if the game is still in progress.
        """
        def has_won(player: Player) -> bool:
            cells_marked = list(map(lambda m: m.cell, self.get_noughts() if player.symbol.is_nought else self.get_crosses()))
            for row in self._get_rows():
                if len(cells_marked) >= self.grid.dim and all(list(map(lambda cell: cell in cells_marked, row))):
                    return True
            for col in self._get_columns():
                if len(cells_marked) >= self.grid.dim and all(list(map(lambda cell: cell in cells_marked, col))):
                    return True
            return len(cells_marked) >= self.grid.dim and \
                (all(list(map(lambda cell: cell in cells_marked, self._get_diagonal()))) or \
                all(list(map(lambda cell: cell in cells_marked, self._get_antidiagonal()))))

        for player in self.players:
            if has_won(player):
                self.logger.debug(f"The {player} has won")
                return player
        self.logger.debug(f"Game not ended")
        return None

    def reset_grid(self):
        """Clear all marks and recreate a fresh grid of the same dimension."""
        self.marks = list()
        self.grid = Grid(self.grid.dim)
        self.logger.debug(f"Reset grid")

    def update(self, delta_time: float):
        """Advance the game state by one update cycle.

        :param delta_time: The elapsed time since the previous update.
        """
        self.updates += 1
        self.time += delta_time
        self.logger.debug(f"Update {self.updates} (time: {self.time})")

    def get_turn_player(self) -> Player:
        """Return the active player.

        :return: The active player.
        """
        return list(filter(lambda p: p.symbol == self.turn, self.players))[0]

    def change_turn(self):
        """Switch turn to the other player."""
        self.turn = Symbol.CROSS if self.turn.is_nought else Symbol.NOUGHT
        self.logger.debug(f"Change turn. Now the player '{self.turn.value}' is in turn")

    def override(self, other: 'TicTacToe'):
        """Override this :class:`TicTacToe` instance with the one given.

        :param other: The new game state to override with.
        """
        if self == other:
            return
        self.logger.debug(f"Overriding TicTacToe status")
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

    def _get_diagonal(self) -> List[Cell]:
        return list(filter(lambda c: c.x == c.y, self.grid.cells))

    def _get_antidiagonal(self) -> List[Cell]:
        reversed_cells = self._get_rows().copy()
        return [reversed_cells[i][-(i+1)] for i in range(len(reversed_cells))]

    def _get_columns(self) -> List[List[Cell]]:
        res = list()
        for i in range(self.grid.dim):
            col = list(filter(lambda c: c.x == i, self.grid.cells))
            res.append(col)
        return res

    def _get_rows(self) -> List[List[Cell]]:
        res = list()
        for j in range(self.grid.dim):
            row = list(filter(lambda c: c.y == j, self.grid.cells))
            res.append(row)
        return res
