import unittest

from tic_tac_toe import TicTacToe
from tic_tac_toe.model.game_object import Mark, Symbol, Player
from tic_tac_toe.model.grid import Cell
import tic_tac_toe.remote.presentation as presentation
from pygame.event import Event
import json
import pathlib

DIR_CURRENT = pathlib.Path(__file__).parent

class TestPresentation(unittest.TestCase):
    def setUp(self):
        tic_tac_toe = TicTacToe(size=(600, 600))
        tic_tac_toe.players = [Player(Symbol.CROSS), Player(Symbol.NOUGHT)]
        tic_tac_toe.place_mark(Mark(
            cell=Cell(0, 1),
            symbol=Symbol.CROSS,
            size=(tic_tac_toe.size / tic_tac_toe.grid.dim),
            position=tic_tac_toe.config.cells_symbol_position.get((0, 1))
        ))
        tic_tac_toe.place_mark(Mark(
            cell=Cell(2, 2),
            symbol=Symbol.NOUGHT,
            size=(tic_tac_toe.size / tic_tac_toe.grid.dim),
            position=tic_tac_toe.config.cells_symbol_position.get((2, 2))
        ))
        tic_tac_toe.update(1.5)
        self.event = Event(1, {"state": tic_tac_toe})
        self.serialized_event = (DIR_CURRENT / "expected.json").read_text()

    def test_serialize_event(self):
        actual = json.loads(presentation.serialize(self.event))
        expected = json.loads(self.serialized_event)
        self.assertEqual(actual, expected)

    def test_deserialize_event(self):
        actual = presentation.deserialize(self.serialized_event)
        expected = self.event
        self.assertEqual(actual, expected)
