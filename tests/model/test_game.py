from unittest import TestCase
from tic_tac_toe.model.game import *

class TestTicTacToe(TestCase):
    def setUp(self) -> None:
        self.screen_size = Vector2(600, 600)
        self.dim = 3
        self.tictactoe = TicTacToe(size=self.screen_size, dim=self.dim)
        self.expected_config = Config(
            self.dim,
            self.screen_size.x / self.dim,
            self.screen_size.y / self.dim
        )

    def test_initial_config(self):
        self.assertEqual(self.tictactoe.config, self.expected_config)

    def test_initial_marks(self):
        self.assertEqual(self.tictactoe.marks, list())
    
    def test_place_mark(self):
        cell = Cell(0, 0)
        mark = Mark(cell, Symbol.CROSS)
        self.tictactoe.place_mark(mark)
        self.tictactoe.place_mark(mark)
        self.assertEqual(1, self.tictactoe.marks.__len__())
        self.assertTrue(self.tictactoe.has_mark(cell))
        self.assertTrue(self.tictactoe.turn == Symbol.NOUGHT)
        self.assertTrue(self.tictactoe.marks.__contains__(mark))

    def test_remove_mark(self):
        cell = Cell(0, 0)
        self.tictactoe.place_mark(Mark(cell, Symbol.CROSS))
        self.tictactoe.remove_mark(cell)
        self.assertEqual(0, self.tictactoe.marks.__len__())
        with self.assertRaises(ValueError):
            self.tictactoe.remove_mark(cell)
