"""
DW Reference: NPC AI (Book 1, p.84-85).
Purpose: Modularize enemy AI decisions - reduce spam, batch decisions.
Dependencies: client/enemy.py for Enemy class; core/hex/utils.py for dist.
Ext Hooks: Add new behaviors; integrate with Actor stats.
Game Loop: Called from CombatSystem for planning; no rendering.
"""

from core.hex.utils import hex_distance

class AISystem:
    """
    Handles AI decision-making for enemies: chooses behaviors, plans paths.
    - Reduces spam by batching; modular for extensibility.
    - Dependencies: Enemy.calculate_ai_path for pathfinding.
    - Grand Scheme: Separates AI from game loop; called only in combat plan phase.
    """

    def __init__(self, grid_tiles):
        """
        Init with grid reference for AI path calculations.
        - grid_tiles: Dict for Enemy.calculate_ai_path blocker checks.
        """
        self.grid_tiles = grid_tiles
        self.last_decide_time = 0.0  # Throttle full decisions

    def decide_actions_batch(self, enemies, player_pos, delta_time=0.5):
        """
        Batch AI decisions for all enemies; call in combat planning.
        - Sets enem.planned_path and enem.attack_this_turn.
        - Throttled to delta_time to prevent spam; returns if too soon.
        - Returns list of (enem, path) for CombatSystem to store.
        """
        import time
        current_time = time.time()
        if current_time - self.last_decide_time < delta_time:
            return []  # Throttled
        self.last_decide_time = current_time

        actions = []
        for enem in enemies:
            if enem.hp > 0:
                decision = self._decide_single_action(enem, player_pos, enemies)
                actions.append((enem, decision['path'], decision['attack']))
        return actions

    def _decide_single_action(self, enem, player_pos, enemies):
        """
        Private: Decide one enemy's action - behavior, path, attack.
        - Behavior: chase if close, patrol if far, retreat if low HP.
        - Returns dict: {'path': list or None, 'attack': bool}
        """
        dist = hex_distance(enem.pos[0], enem.pos[1], player_pos[0], player_pos[1])
        behavior = 'chase' if dist <= enem.chase_distance else 'patrol'
        if enem.hp <= enem.max_hp * enem.retreat_threshold:
            behavior = 'retreat'

        path = enem.calculate_ai_path(player_pos, self.grid_tiles, enemies, behavior)
