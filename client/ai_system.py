"""
DW Reference: NPC AI behaviors (Book 1, p.84-85, pp. 39-42 for tactical AI in combat).
Purpose: Modular AI system for enemy behaviors - decoupled from main loop to reduce spam and clutter.
Dependencies: client/enemy.py for Enemy; client/game_state.py for state access; core/hex/utils.py for distance.
Ext Hooks: Future behavior plugins (e.g., patrol patterns); integrates with CombatSystem in Step 2.
Combat Only: Called from game.py tick loop only in combat; exploration enemies idle.
"""

import time
from client.game_state import GameState
from client.enemy import Enemy
from core.hex.utils import hex_distance

class AISystem:
    """
    Manages enemy AI decisions and path planning with throttling to avoid spam.
    - Manages all enemy behaviors: chase, retreat, patrol based on rules/GD.
    - Decoupled from main loop; uses Enemy.calculate_ai_path for plans.
    - Grand Scheme: Reduces enemy print noise in game.py; enables batch AI updates.
    """

    def __init__(self, state: GameState, grid_tiles):
        """
        Init with state and grid; ai_system manages AI logic centrally.
        - state: Access to enemies, player pos, etc.
        - grid_tiles: For path calculation blockers/st теж.
        """
        self.state = state
        self.grid_tiles = grid_tiles
        self.last_ai_update = 0.0  # Throttle batch AI calls to reduce spam/performance hits
        self.ai_interval = 1.0  # Update AI every 1s; adjustable per GD for balancing

    def update_ai(self, enemies, player_pos):
        """
        Batch update all enemy AI behaviors if enough time passed (reduce spam).
        - Called from game.py tick only in combat mode.
        - Each enemy decides behavior state (chase/retreat/patrol) and plans path.
        - Throttled to 1/s; silent execution for less noise.
        """
        current_time = time.time()
        if current_time - self.last_ai_update < self.ai_interval:
            return  # Skip frequent updates

        self.last_ai_update = current_time

        for enem in enemies:
            if enem.hp > 0 and not enem.is_moving:  # Avoid interrupting movement
                # Decide behavior based on GD rules
                behavior, target_pos = self._decide_behavior(enem, self.state.player_hp, player_pos)

                if behavior == 'chase':
                    # Find adjacent free hex to pursue player safely
                    closest_free = enem.find_free_hex_adjacent_to_target(player_pos, self.grid_tiles, occupied={tuple(enemy.pos) for enemy in enemies if enemy.hp > 0 and enemy != enem})
                    target_pos = closest_free if closest_free else target_pos
                elif behavior == 'retreat':
                    # Find furthest hex within MV to flee
                    retreat_pos = enem.find_retreat_position(player_pos, self.grid_tiles, occupied={tuple(enemy.pos) for enemy in enemies if enemy.hp > 0 and enemy != enem})
                    target_pos = retreat_pos if retreat_pos else enem.pos
                # Patrol uses random nearby hex by default

                # Plan path if target differs
                if target_pos != enem.pos:
                    path = enem.calculate_ai_path(player_pos, self.grid_tiles, enemies, behavior, occupied={tuple(enemy.pos) for enemy in enemies if enemy.hp > 0 and enemy != enem})
                    if path:
                        enem.start_movement(path)  # Will execute via enemy loop
                        # Silent planning; avoid spam prints

    def _decide_behavior(self, enemy, player_hp, player_pos):
        """
        Decide enemy behavior per GD (10 hex chase, retreat if low HP or player defeated).
        - Returns (behavior, target_pos) tuple for path calculation.
        """
        # Lose interest if player is defeated
        if player_hp <= 0:
            return 'patrol', enemy.pos

        dist = hex_distance(enemy.pos[0], enemy.pos[1], player_pos[0], player_pos[1])

        # Retreat if HP low (GD: below 30%)
        if enemy.hp <= enemy.max_hp * 0.3:
            return 'retreat', enemy.pos  # Anytime, even if moving

        # Chase within range (GD: 10+ but tune to 15 hex)
        if dist <= 15:
            return 'chase', player_pos

        # Default patrol (random nearby)
        return 'patrol', enemy.pos
