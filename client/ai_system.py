""" DW Reference: NPC AI (Book 1, p.84-85).
Purpose: Modularize enemy AI decisions - reduce spam, batch decisions.
Dependencies: client/enemy.py for Enemy class; core/hex/utils.py for dist.
Ext Hooks: Add new behaviors; integrate with Actor stats.
Game Loop: Called from CombatSystem for planning; no rendering.
"""
from core.hex.utils import hex_distance
import time

class AISystem:
    """
    Handles AI decision-making for enemies in combat scenarios.
    
    This system manages batch processing of enemy AI decisions to reduce computational overhead
    and prevent spam. It determines behaviors (chase, patrol, retreat) and plans paths for all
    enemies simultaneously during combat planning phases.
    """

    def __init__(self, state, grid_tiles):
        """
        Initialize the AI system with game state and grid references.
        
        Args:
            state (GameState): Central game state object for accessing game data
            grid_tiles (dict): Grid tiles for pathfinding and collision detection
        """
        self.state = state
        self.grid_tiles = grid_tiles
        self.last_decide_time = 0.0  # Throttle full decisions to prevent spam

    def decide_actions_batch(self, enemies, player_pos, delta_time=0.5):
        """
        Batch process AI decisions for all living enemies in combat.
        
        This method determines behaviors and plans paths for all enemies simultaneously
        during the combat planning phase, reducing computational overhead and ensuring
        consistent timing across all enemy actions.
        
        Args:
            enemies (list): List of enemy objects to process
            player_pos (tuple): Player's current position (q, r)
            delta_time (float): Minimum time interval between AI decisions in seconds
            
        Returns:
            list: List of tuples containing (enemy, path, attack_flag) for CombatSystem processing
        """
        if not self._should_decide_actions(delta_time):
            return []
        actions = []
        for enem in enemies:
            if enem.hp > 0:
                decision = self._decide_single_action(enem, player_pos, enemies)
                actions.append((enem, decision['path'], decision['attack']))
        return actions

    def _should_decide_actions(self, delta_time):
        """
        Check if enough time has passed since last AI decision to prevent spam.
        
        Args:
            delta_time (float): Minimum time interval between decisions in seconds
			
        Returns:
            bool: True if it's time to make new decisions, False otherwise
        """
        current_time = time.time()
        if current_time - self.last_decide_time < delta_time:
            return False
        self.last_decide_time = current_time
        return True

    def _decide_single_action(self, enem, player_pos, enemies):
        """
        Decide AI action for a single enemy including behavior, path planning, and attack decisions.
        
        This method determines the appropriate behavior based on enemy health, distance to player,
        and game state, then calculates the optimal path and attack decision accordingly.
        
        Args:
            enem (Enemy): Enemy object to make decisions for
            player_pos (tuple): Player's current position (q, r)
            enemies (list): List of all enemies for collision detection
            
        Returns:
            dict: Dictionary containing 'path' and 'attack' flags for the enemy action
        """
        dist = hex_distance(enem.pos[0], enem.pos[1], player_pos[0], player_pos[1])
        behavior = 'chase' if dist <= enem.chase_distance else 'patrol'
        if enem.hp <= enem.max_hp * enem.retreat_threshold:
            behavior = 'retreat'
        path = enem.calculate_ai_path(player_pos, self.grid_tiles, enemies, behavior)
        decision = {'path': None, 'attack': False}
        if path:
            decision['path'] = path
            if dist <= enem.chase_distance:
                decision['attack'] = True
        return decision
