import threading
from unittest import TestCase
from pygame import Vector2
from tic_tac_toe import TicTacToeGame
from tic_tac_toe.controller import EventHandler, InputHandler
from tic_tac_toe.model.game_object import Player, Symbol
from tic_tac_toe.utils import Settings
from tic_tac_toe.view import ShowNothingTicTacToeView

class TestTicTacToeGame(TestCase):
    def setUp(self) -> None:
        self.settings = Settings(size=Vector2(600, 600), dim=3, gui=False, debug=True)
        self.players = [Player(Symbol.NOUGHT), Player(Symbol.CROSS)]
        self.game = TicTacToeGame(settings=self.settings, players=self.players)
        self.thread = threading.Thread(target=self.game.run)
        self.thread.start()

    def test_initial_config(self) -> None:
        print(self.game.running)
        self.assertEqual(self.settings, self.game.settings)
        self.assertEqual(self.players, self.game.tic_tac_toe.players)
        self.assertTrue(self.game.running)

    def test_controller_and_view(self) -> None:
        self.assertIsNotNone(self.game.controller)
        self.assertIsNotNone(self.game.view)
        self.assertIsInstance(self.game.controller, InputHandler)
        self.assertIsInstance(self.game.controller, EventHandler)
        self.assertIsInstance(self.game.view, ShowNothingTicTacToeView)

    def test_game_loop(self) -> None:
        self.assertTrue(self.game.running)
        self.game.stop()
        self.assertFalse(self.game.running)

    def tearDown(self) -> None:
        self.game.stop()
        self.thread.join(timeout=1)
