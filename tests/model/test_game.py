from unittest import TestCase
from tic_tac_toe.model import *

class TestTicTacToe(TestCase):
    def setUp(self) -> None:
        self.screen_size = Vector2(600, 600)
        self.dim = 3
        self.tictactoe = TicTacToe(
            size=self.screen_size,
            dim=self.dim,
            players=[Player(Symbol.NOUGHT)]
        )
        self.expected_config = Config(
            self.screen_size.x / self.dim,
            self.screen_size.y / self.dim
        )

    def test_initial_config(self):
        self.assertEqual(self.tictactoe.config, self.expected_config)
        self.assertEqual(Symbol.CROSS, self.tictactoe.turn)
        self.assertListEqual([Player(Symbol.NOUGHT)], self.tictactoe.players)

    def test_add_player(self):
        self.tictactoe.add_player(Player(Symbol.CROSS))
        self.assertEqual([Player(Symbol.NOUGHT), Player(Symbol.CROSS)], self.tictactoe.players)
        with self.assertRaises(AssertionError):
            self.tictactoe.add_player(Player(Symbol.CROSS))

    def test_remove_player(self):
        self.tictactoe.remove_player_by_symbol(Symbol.NOUGHT)
        self.assertEqual([], self.tictactoe.players)
        with self.assertRaises(ValueError):
            self.tictactoe.remove_player_by_symbol(Symbol.NOUGHT)

    def test_get_turn_player(self):
        self.tictactoe.players = [Player(Symbol.CROSS), Player(Symbol.NOUGHT)]
        self.assertEqual(self.tictactoe.players[0], self.tictactoe.get_turn_player())
        self.tictactoe.change_turn()
        self.assertEqual(self.tictactoe.players[1], self.tictactoe.get_turn_player())


    def test_initial_marks(self):
        self.assertEqual(self.tictactoe.marks, list())
    
    def test_place_mark(self):
        cell = Cell(0, 0)
        mark = Mark(cell, Symbol.CROSS)
        self.assertTrue(self.tictactoe.place_mark(mark))
        self.assertFalse(self.tictactoe.place_mark(mark))
        self.assertEqual(1, self.tictactoe.marks.__len__())
        self.assertTrue(self.tictactoe.has_mark(cell))

    def test_remove_mark(self):
        cell = Cell(0, 0)
        self.tictactoe.place_mark(Mark(cell, Symbol.CROSS))
        self.tictactoe.remove_mark(cell)
        self.assertEqual(0, self.tictactoe.marks.__len__())
        with self.assertRaises(ValueError):
            self.tictactoe.remove_mark(cell)
