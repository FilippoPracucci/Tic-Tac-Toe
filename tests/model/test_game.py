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
        with self.assertRaises(ValueError):
            self.tictactoe.add_player(Player(Symbol.CROSS))

    def test_remove_player(self):
        self.tictactoe.remove_player_by_symbol(Symbol.NOUGHT)
        self.assertEqual([], self.tictactoe.players)
        with self.assertRaises(ValueError):
            self.tictactoe.remove_player_by_symbol(Symbol.NOUGHT)

    def test_is_player_lobby_full(self):
        self.tictactoe.players = [Player(Symbol.CROSS), Player(Symbol.NOUGHT)]
        self.assertTrue(self.tictactoe.is_player_lobby_full())

    def test_is_player_lobby_not_full(self):
        self.tictactoe.players = [Player(Symbol.CROSS)]
        self.assertFalse(self.tictactoe.is_player_lobby_full())

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
        self.assertEqual(1, len(self.tictactoe.marks))
        self.assertTrue(self.tictactoe.has_mark(cell))

    def test_remove_mark(self):
        cell = Cell(0, 0)
        self.tictactoe.place_mark(Mark(cell, Symbol.CROSS))
        self.tictactoe.remove_mark(cell)
        self.assertEqual(0, len(self.tictactoe.marks))
        with self.assertRaises(ValueError):
            self.tictactoe.remove_mark(cell)

    def test_override(self):
        other = TicTacToe(Settings.size, players=[Player(Symbol.CROSS)])
        other.marks = [Mark(Cell(0, 2), Symbol.CROSS), Mark(Cell(0, 0), Symbol.NOUGHT), Mark(Cell(1, 2), Symbol.CROSS)]
        self.tictactoe.players = [Player(Symbol.NOUGHT)]
        self.tictactoe.marks = [Mark(Cell(0, 1), Symbol.CROSS), Mark(Cell(0, 0), Symbol.NOUGHT)]
        self.tictactoe.override(other)
        self.assertEqual(other, self.tictactoe)
