import unittest
from core.pathfinding.a_star import a_star, is_path_valid, get_path_cost, PathfindingError
from client.map.tile import Tile


class TestPathfinding(unittest.TestCase):
    def setUp(self):
        """Create a simple grid for testing."""
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
        """Test basic pathfinding from (0,0) to (1,0)."""
        path = a_star((0, 0), (1, 0), self.grid)
        self.assertEqual(path, [(0, 0), (1, 0)])

    def test_no_path_blocked(self):
        """Test that blocked tiles prevent pathfinding."""
        self.grid[(1, 0)].blocked = True
        path = a_star((0, 0), (1, 0), self.grid)
        self.assertEqual(path, [])

    def test_same_start_goal(self):
        """Test pathfinding when start equals goal."""
        path = a_star((0, 0), (0, 0), self.grid)
        self.assertEqual(path, [(0, 0)])

    def test_movement_limit(self):
        """Test max_distance parameter limits path length."""
        path = a_star((0, 0), (1, 1), self.grid, max_distance=1)
        # Should be limited to 1 move (start + 1 hex)
        self.assertEqual(len(path), 2)

    def test_path_validation(self):
        """Test is_path_valid function."""
        valid_path = [(0, 0), (1, 0)]
        self.assertTrue(is_path_valid(valid_path, self.grid))
        
        invalid_path = [(0, 0), (999, 999)]
        self.assertFalse(is_path_valid(invalid_path, self.grid))

    def test_path_cost(self):
        """Test get_path_cost function."""
        path = [(0, 0), (1, 0), (1, 1)]
        cost = get_path_cost(path, self.grid)
        self.assertEqual(cost, 2)  # 1 + 1

    def test_invalid_start(self):
        """Test that invalid start position raises error."""
        with self.assertRaises(PathfindingError):
            a_star((999, 999), (0, 0), self.grid)

    def test_invalid_goal(self):
        """Test that invalid goal position raises error."""
        with self.assertRaises(PathfindingError):
            a_star((0, 0), (999, 999), self.grid)

    def test_complex_path(self):
        """Test pathfinding through a more complex grid."""
        grid = {
            (0, 0): Tile('plain'), (1, 0): Tile('plain'), (2, 0): Tile('plain'),
            (0, 1): Tile('plain'), (1, 1): Tile('plain'), (2, 1): Tile('plain'),
            (0, 2): Tile('plain'), (1, 2): Tile('plain'), (2, 2): Tile('plain'),
        }
        for tile in grid.values():
            tile.cost = 1
            tile.blocked = False
        
        path = a_star((0, 0), (2, 2), grid)
        self.assertIsNotNone(path)
        self.assertEqual(path[0], (0, 0))
        self.assertEqual(path[-1], (2, 2))
        self.assertTrue(is_path_valid(path, grid))

    def test_path_with_obstacles(self):
        """Test pathfinding around obstacles."""
        grid = {
            (0, 0): Tile('plain'), (1, 0): Tile('plain'), (2, 0): Tile('plain'),
            (0, 1): Tile('plain'), (1, 1): Tile('plain'), (2, 1): Tile('plain'),
            (0, 2): Tile('plain'), (1, 2): Tile('plain'), (2, 2): Tile('plain'),
        }
        for tile in grid.values():
            tile.cost = 1
            tile.blocked = False
        
        # Block the direct path
        grid[(1, 1)].blocked = True
        
        path = a_star((0, 0), (2, 2), grid)
        self.assertIsNotNone(path)
        # Should find a path around the obstacle
        self.assertTrue(is_path_valid(path, grid))


if __name__ == '__main__':
    unittest.main()