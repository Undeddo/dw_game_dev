import unittest
from core.hex.utils import get_neighbors, hex_distance


class TestHexUtils(unittest.TestCase):
    def test_hex_distance(self):
        # Test distance between same hex
        self.assertEqual(hex_distance(0, 0, 0, 0), 0)
        # Test distance between adjacent hexes
        self.assertEqual(hex_distance(0, 0, 1, 0), 1)
        self.assertEqual(hex_distance(0, 0, 0, 1), 1)
        self.assertEqual(hex_distance(0, 0, -1, 0), 1)
        self.assertEqual(hex_distance(0, 0, 0, -1), 1)
        # Test diagonal (should be max of |dq|, |dr|, |dq + dr|)
        self.assertEqual(hex_distance(0, 0, 1, 1), 1)
        self.assertEqual(hex_distance(0, 0, 2, 1), 2)

    def test_get_neighbors(self):
        # Neighbors of (0,0)
        expected = {(1,0), (0,1), (-1,1), (-1,0), (0,-1), (1,-1)}
        self.assertEqual(set(get_neighbors(0, 0)), expected)
        # Test another hex
        expected = {(2,1), (1,2), (0,2), (0,1), (1,0), (2,0)}
        self.assertEqual(set(get_neighbors(1, 1)), expected)


if __name__ == '__main__':
    unittest.main()
