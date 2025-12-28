"""
Test file for ActorStats integration in enemy system.
This verifies that enemies can properly use ActorStats for their attributes.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from client.actors.base import ActorStats
from client.enemy import Enemy

def test_enemy_with_stats():
    """Test that enemy can be created with custom stats."""
    # Create custom stats
    stats = ActorStats(name="TestEnemy", str=12, agi=8, mv=5)
    
    # Create enemy with stats
    enemy = Enemy(start_pos=(0, 0), stats=stats)
    
    # Verify stats are properly assigned
    assert enemy.stats == stats
    assert enemy.hp > 0  # HP is calculated automatically
    assert enemy.max_hp > 0  # Max HP is calculated automatically
    assert enemy.stats.str == 12
    assert enemy.stats.agi == 8
    
    print("✓ Enemy with custom stats created successfully")
    return True

def test_enemy_default_stats():
    """Test that enemy defaults to reasonable stats when none provided."""
    # Create enemy without explicit stats
    enemy = Enemy(start_pos=(0, 0))
    
    # Verify default stats are assigned
    assert enemy.stats is not None
    assert enemy.hp > 0
    assert enemy.max_hp > 0
    assert enemy.stats.str == 8  # Default value
    assert enemy.stats.agi == 8  # Default value
    
    print("✓ Enemy with default stats created successfully")
    return True

if __name__ == "__main__":
    print("Testing ActorStats integration...")
    
    try:
        test_enemy_with_stats()
        test_enemy_default_stats()
        print("\n✓ All tests passed!")
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
