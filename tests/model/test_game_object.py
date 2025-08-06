from unittest import TestCase
from tic_tac_toe.model.game_object import *

class TestGameObject(TestCase):
    SIZE = Vector2(500, 400)
    POSITION = Vector2(150, 200)

    gameObject = GameObject(SIZE, POSITION, "game_object")

    def test_size(self):
        new_size = (600, 600)
        self.assertEqual(Vector2(self.SIZE), self.gameObject.size)
        self.gameObject.size = (new_size)
        self.assertEqual(Vector2(new_size), self.gameObject.size)

    def test_position(self):
        new_position = (300, 300)
        self.assertEqual(Vector2(self.POSITION), self.gameObject.position)
        self.gameObject.position = new_position
        self.assertEqual(Vector2(new_position), self.gameObject.position)
