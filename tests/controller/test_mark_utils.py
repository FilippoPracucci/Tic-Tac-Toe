from unittest import TestCase
from tic_tac_toe.model.grid import Cell
from tic_tac_toe.controller.mark_utils import *

class TestMarkUtils(TestCase):
    mark1 = Mark(Cell(0, 0), Symbol.CROSS)
    mark2 = Mark(Cell(1, 2), Symbol.NOUGHT)
    marks = [mark1, mark2]

    def setUp(self) -> None:
        self.mark_utils = MarkUtils()
        self.mark_views = self.mark_utils.decompose(self.marks)

    def test_decompose(self):
        for view in self.mark_views:
            self.assertIsInstance(view, MarkView)

    def test_mark_view(self):
        self.assertEqual(self.mark1.symbol.value, self.mark_views[0].symbol)
        self.assertEqual((self.mark1.cell.x, self.mark1.cell.y), self.mark_views[0].cell)
        self.assertEqual((self.mark1.position.x, self.mark1.position.y), self.mark_views[0].position)
