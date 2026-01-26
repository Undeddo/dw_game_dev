#!/usr/bin/env python3
"""
Test script to verify movement works correctly at screen edges.
This tests the coordinate conversion fixes.
"""

import sys
sys.path.insert(0, '.')

from client.movement_controller import MovementController
from client.map.hex_grid import HexGrid

def test_edge_coordinate_conversions():
    """Test that coordinate conversions work at screen edges."""
    print("Testing edge case coordinate conversions...")

    # Create a grid and movement controller
    grid = HexGrid(size=10, hex_size=50)
    mc = MovementController(
        grid=grid.tiles,
        hex_size=grid.hex_size,
        screen_width=1024,
        screen_height=768
    )

    # Test 1: Convert edge hexes to screen coordinates
    print("\nTest 1: Edge hex to screen conversion")
    edge_hexes = [
        (-5, -5),  # Bottom-left corner (may be partially off-screen)
        (4, -5),   # Bottom-right corner
        (-5, 4),   # Top-left corner
        (4, 4)     # Top-right corner
    ]

    for q, r in edge_hexes:
        screen_pos = mc.hex_to_screen(q, r)
        print(f"Hex ({q}, {r}) -> Screen {screen_pos}")
        # Note: Some edge hexes may render partially off-screen, which is expected
        # The important thing is that the conversion works without errors

    # Test 2: Convert screen edge positions to hex coordinates
    print("\nTest 2: Screen edge to hex conversion")
    screen_edges = [
        (0, 0),           # Top-left corner
        (1023, 0),        # Top-right corner
        (0, 767),         # Bottom-left corner
        (1023, 767),      # Bottom-right corner
        (512, 0),         # Top center
        (512, 767),       # Bottom center
        (0, 384),         # Left center
        (1023, 384)       # Right center
    ]

    for x, y in screen_edges:
        hex_pos = mc.screen_to_hex(x, y)
        if hex_pos:
            print(f"Screen ({x}, {y}) -> Hex {hex_pos}")
            assert hex_pos in grid.tiles, f"Invalid hex position: {hex_pos}"
        else:
            print(f"Screen ({x}, {y}) -> No valid hex (edge case handled)")

    # Test 3: Verify round-trip consistency
    print("\nTest 3: Round-trip conversion consistency")
    test_hexes = [(-5, -4), (-2, 0), (0, 0), (3, 2), (4, 4)]

    for q, r in test_hexes:
        screen_pos = mc.hex_to_screen(q, r)
        back_to_hex = mc.screen_to_hex(screen_pos[0], screen_pos[1])
        print(f"Hex ({q}, {r}) -> Screen {screen_pos} -> Hex {back_to_hex}")
        assert back_to_hex == (q, r), f"Round-trip failed: {(q, r)} != {back_to_hex}"

    # Test 4: Verify axial_round handles edge cases
    print("\nTest 4: Axial rounding at edges")
    edge_cases = [
        (-5.9, -5.1),   # Just outside bottom-left
        (4.8, -5.2),    # Just outside bottom-right
        (-5.3, 4.7),    # Just outside top-left
        (4.6, 4.9)      # Just outside top-right
    ]

    for q, r in edge_cases:
        rounded = mc.axial_round(q, r)
        if rounded:
            print(f"Rounded ({q}, {r}) -> {rounded}")
            assert rounded in grid.tiles, f"Rounded to invalid position: {rounded}"
        else:
            print(f"Rounded ({q}, {r}) -> None (no valid hex nearby)")

    print("\n✅ All edge case tests passed!")
    return True

if __name__ == "__main__":
    try:
        test_edge_coordinate_conversions()
        print("\n🎉 Movement system edge cases are working correctly!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)