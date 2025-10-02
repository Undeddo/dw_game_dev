import unittest
from core.pathfinding.a_star import a_star
from client.map.tile import Tile


class TestPathfinding(unittest.TestCase):
    def setUp(self):
        # Create a simple grid for testing
        self.grid = {
            (0, 0): Tile('plain'),  # cost 1
            (1, 0): Tile('plain'),
            (0, 1): Tile('plain'),
            (1, 1): Tile('plain'),
        }
        # Set cost to 1 for plain
        for tile in self.grid.values():
            tile.cost = 1
            tile.blocked = False

    def test_simple_path(self):
        path = a_star((0, 0), (1, 0), self.grid)
        self.assertEqual(path, [(0, 0), (1, 0)])

    def test_no_path_blocked(self):
        # Block the way
        self.grid[(1, 0)].blocked = True
        path = a_star((0, 0), (1, 0), self.grid)
        self.assertEqual(path, [])

    def test_same_start_goal(self):
        path = a_star((0, 0), (0, 0), self.grid)
        self.assertEqual(path, [(0, 0)])

    def test_movement_limit(self):
        # Test max_distance parameter
        path = a_star((0, 0), (1, 1), self.grid, max_distance=1)
        # Should be limited to 1 hex
        self.assertEqual(len(path), 2)  # start + 1 move, since distance=1 allows 1 hex


if __name__ == '__main__':
    unittest.main()
