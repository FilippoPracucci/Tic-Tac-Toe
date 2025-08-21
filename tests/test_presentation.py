import unittest
from tic_tac_toe import TicTacToe
from tic_tac_toe.model.game_object import Mark, Symbol
from tic_tac_toe.model.grid import Cell
import tic_tac_toe.remote.presentation as presentation
from pygame.event import Event
import json
import pathlib

DIR_CURRENT = pathlib.Path(__file__).parent

class TestPresentation(unittest.TestCase):
    def setUp(self):
        tic_tac_toe = TicTacToe(size=(600, 600))
        tic_tac_toe.marks = [Mark(Cell(0, 1), Symbol.CROSS), Mark(Cell(2, 2), Symbol.NOUGHT)]
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
