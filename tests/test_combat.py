import unittest
from client.combat_system import CombatSystem
from client.game_state import GameState
from client.enemy import Enemy
from core.hex.grid import HexGrid


class TestCombatSystem(unittest.TestCase):
    def setUp(self):
        # Create a simple grid for testing
        grid = HexGrid(size=10, hex_size=50)
        enemies = [Enemy(start_pos=(0, 1), mv_limit=6)]
        state = GameState(enemies=enemies)
        self.combat_system = CombatSystem(state, grid.tiles, grid)

    def test_plan_player_path(self):
        # Test planning a player path
        goal_hex = (1, 1)
        result = self.combat_system.plan_player_path(goal_hex)
        self.assertTrue(result)

    def test_resolve_1v1_combat(self):
        # Test resolving 1-on-1 combat
        self.combat_system._resolve_1v1_combat()
        # Check if the enemy is defeated
        alive_enemies = [enem for enem in self.combat_system.state.enemies if enem.hp > 0]
        self.assertEqual(len(alive_enemies), 1)

    def test_combat_system_initialization(self):
        # Test CombatSystem initialization
        self.assertIsNotNone(self.combat_system.state)
        self.assertIsNotNone(self.combat_system.grid_tiles)
        self.assertIsNotNone(self.combat_system.grid)
        self.assertEqual(len(self.combat_system.enemy_planned_paths), 0)
        self.assertEqual(self.combat_system.last_enemy_plan_time, 0.0)

    def test_plan_player_path_invalid(self):
        # Test planning a player path with invalid goal
        goal_hex = (99, 99)  # Invalid goal
        result = self.combat_system.plan_player_path(goal_hex)
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()