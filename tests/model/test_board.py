from unittest import TestCase
from tic_tac_toe.model.grid import *
from tic_tac_toe.model.game_object import Player, Symbol, Mark

class TestSymbol(TestCase):
    def test_is_nought(self):
        self.assertTrue(Symbol.NOUGHT.is_nought)
        self.assertFalse(Symbol.CROSS.is_nought)

    def test_is_cross(self):
        self.assertTrue(Symbol.CROSS.is_cross)
        self.assertFalse(Symbol.NOUGHT.is_cross)

    def test_opposite(self):
        self.assertEqual(Symbol.CROSS, Symbol.NOUGHT.opposite)
        self.assertEqual(Symbol.NOUGHT, Symbol.CROSS.opposite)

class TestPlayer(TestCase):
    def test_create_player(self):
        player = Player(Symbol.CROSS)
        self.assertEqual(Symbol.CROSS, player.symbol)

class TestMark(TestCase):
    def test_create_mark(self):
        mark = Mark(Cell(0, 0), Symbol.NOUGHT)
        self.assertEqual(Symbol.NOUGHT, mark.__getattribute__("symbol"))
        self.assertEqual(Cell(0, 0), mark.__getattribute__("cell"))

    def test_mark_override(self):
        initial_mark = Mark(Cell(0, 0), Symbol.NOUGHT)
        override_mark = Mark(Cell(0, 0), Symbol.CROSS)
        initial_mark.override(override_mark)
        self.assertEqual(override_mark, initial_mark)

class TestGrid(TestCase):
    def test_create_grid(self):
        dim: int = 3
        grid: Grid = Grid(dim)
        cells: List[Cell] = list(Cell(i, j) for i in range(dim) for j in range(dim))
        self.assertEqual(dim, grid.dim)
        self.assertEqual(cells, grid.cells)
