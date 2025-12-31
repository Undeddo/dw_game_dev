"""Test script to verify path highlighting functionality."""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from client.map.hex_grid import HexGrid
from core.pathfinding.a_star import a_star

def test_path_highlight():
    """Test that path highlighting works correctly."""
    print("Testing path highlight functionality...")

    # Create grid
    grid = HexGrid(size=10, hex_size=50)

    # Test 1: Empty path should not crash
    print("\nTest 1: Setting empty path...")
    grid.set_path_highlight([])
    assert grid.path_highlight == [], "Empty path should be stored correctly"
    print("✓ Empty path handled correctly")

    # Test 2: Setting a valid path
    print("\nTest 2: Setting a valid path...")
    start = [0, 0]
    end = [3, 0]
    tiles = grid.tiles

    path = a_star(start, end, tiles, max_distance=10)
    assert len(path) > 0, "Should find a path from (0,0) to (3,0)"
    print(f"✓ Found path with {len(path)} hexes: {path}")

    grid.set_path_highlight(path)
    assert grid.path_highlight == path, "Path should be stored correctly"
    print("✓ Path stored in grid correctly")

    # Test 3: Replacing path
    print("\nTest 3: Replacing path...")
    new_end = [2, 1]
    new_path = a_star(start, new_end, tiles, max_distance=10)
    assert len(new_path) > 0, "Should find a new path"

    grid.set_path_highlight(new_path)
    assert grid.path_highlight == new_path, "New path should replace old path"
    print("✓ Path replaced correctly")

    # Test 4: Clearing path
    print("\nTest 4: Clearing path...")
    grid.set_path_highlight([])
    assert grid.path_highlight == [], "Path should be cleared"
    print("✓ Path cleared correctly")

    print("\n" + "="*50)
    print("✓ All path highlight tests passed!")
    print("Path highlighting system is working correctly.")
    print("="*50)

if __name__ == "__main__":
    test_path_highlight()
