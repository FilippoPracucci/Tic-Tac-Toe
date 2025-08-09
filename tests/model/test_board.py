from unittest import TestCase
from tic_tac_toe.model.grid import *
from tic_tac_toe.model.game_object import Symbol, Mark

class TestSymbol(TestCase):
    def test_is_nought(self):
        self.assertTrue(Symbol.NOUGHT.is_nought)
        self.assertFalse(Symbol.CROSS.is_nought)

    def test_is_cross(self):
        self.assertTrue(Symbol.CROSS.is_cross)
        self.assertFalse(Symbol.NOUGHT.is_cross)

class TestMark(TestCase):
    def test_create_mark(self):
        mark = Mark(Cell(0, 0), Symbol.NOUGHT)
        self.assertEqual(Symbol.NOUGHT, mark.__getattribute__("symbol"))
        self.assertEqual(Cell(0, 0), mark.__getattribute__("cell"))

class TestGrid(TestCase):
    def test_create_grid(self):
        dim = 3
        grid = Grid(dim)
        cells = list(Cell(i, j) for i in range(dim) for j in range(dim))
        self.assertEqual(dim, grid.dim)
        self.assertEqual(cells, grid.cells)
