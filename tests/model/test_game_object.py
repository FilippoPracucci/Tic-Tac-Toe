from unittest import TestCase
from tic_tac_toe.model.game_object import *

class TestGameObject(TestCase):
    SIZE = Vector2(500, 400)
    POSITION = Vector2(150, 200)

    def setUp(self):
        self.gameObject = GameObject(self.SIZE, self.POSITION, "game_object")

    def test_size(self):
        new_size = Vector2(600, 600)
        self.assertEqual(self.SIZE, self.gameObject.size)
        self.gameObject.size = new_size
        self.assertEqual(new_size ,self.gameObject.size)

    def test_position(self):
        new_position = Vector2(300, 300)
        self.assertEqual(self.POSITION, self.gameObject.position)
        self.gameObject.position = new_position
        self.assertEqual(new_position, self.gameObject.position)

    def test_override(self):
        new_game_object = GameObject(Vector2(600, 600), Vector2(300, 300), self.gameObject.name)
        self.gameObject.override(new_game_object)
        self.assertEqual(new_game_object, self.gameObject)
