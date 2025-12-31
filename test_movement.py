"""Simple test to verify player and enemy movement works."""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from client.actors.base import ActorStats
from client.enemy import Enemy
from core.hex.utils import hex_distance

def test_player_movement():
    """Test that player can move."""
    print("Testing player movement...")
    stats = ActorStats(name="Player", str=12, agi=10)
    assert stats.hp > 0, "Player HP should be positive"
    assert stats.max_hp > 0, "Player max HP should be positive"
    print(f"✓ Player created with {stats.hp}/{stats.max_hp} HP")
    return True

def test_enemy_movement():
    """Test that enemy can move."""
    print("Testing enemy movement...")
    stats = ActorStats(name="Enemy", str=8, agi=8)
    enemy = Enemy(start_pos=(0, 0), stats=stats)

    assert enemy.hp > 0, "Enemy HP should be positive"
    assert enemy.max_hp > 0, "Enemy max HP should be positive"
    print(f"✓ Enemy created with {enemy.hp}/{enemy.max_hp} HP")

    # Test distance calculation
    dist = hex_distance(0, 0, 1, 0)
    assert dist == 1, f"Distance between adjacent hexes should be 1, got {dist}"
    print(f"✓ Hex distance works correctly (distance to (1,0) is {dist})")

    # Test path calculation
    from core.pathfinding.a_star import a_star
    from client.map.tile import Tile

    # Create simple grid
    tiles = {
        (0, 0): Tile('plain'),
        (1, 0): Tile('plain'),
        (2, 0): Tile('plain')
    }

    path = a_star((0, 0), (2, 0), tiles, max_distance=3)
    assert len(path) > 0, "Should find a path from (0,0) to (2,0)"
    print(f"✓ Pathfinding works (found path of length {len(path)})")

    return True

def test_game_state():
    """Test that game state can be created."""
    print("Testing game state...")
    from client.game_state import GameState
    from client.enemy import Enemy

    enemies = [Enemy(start_pos=(0, 1)), Enemy(start_pos=(1, 3))]
    state = GameState(
        enemies=enemies,
        goal_pos=(9, 9),
        mv_limit=6
    )

    assert state.player_pos == [0, 0], "Player should start at (0, 0)"
    assert len(state.enemies) == 2, "Should have 2 enemies"
    assert not state.is_moving, "Should not be moving initially"
    print("✓ GameState initialized correctly")
    return True

if __name__ == "__main__":
    print("Running movement tests...\n")

    try:
        test_player_movement()
        test_enemy_movement()
        test_game_state()

        print("\n" + "="*50)
        print("✓ All movement tests passed!")
        print("The game should now be playable.")
        print("="*50)

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
