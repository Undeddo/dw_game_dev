"""
DW Reference: Enemy AI (Book 1, p.84-85).
Purpose: Enemy AI state machine for chase, patrol, retreat.
Dependencies: core.hex.utils for hex_distance, core.pathfinding.a_star for pathfinding.
Ext Hooks: Add more behaviors like 'guard'.
Client Only: Decision making for enemies.
"""

from core.hex.utils import hex_distance
from core.pathfinding.a_star import a_star


class EnemyAI:
    def __init__(self, enemy, grid_tiles):
        self.enemy = enemy
        self.grid_tiles = grid_tiles

    def decide_behavior(self, player_pos: tuple):
        """Set enemy behavior based on distance and HP."""
        dist = hex_distance(self.enemy.position[0], self.enemy.position[1], player_pos[0], player_pos[1])
        if self.enemy.should_retreat():
            self.enemy.behavior = 'retreat'
        elif dist <= 15:  # Within reasonable chase distance
            self.enemy.behavior = 'chase'
        else:
            self.enemy.behavior = 'patrol'
        self.enemy.is_targeting_player = (self.enemy.behavior == 'chase')

    def calculate_move(self, player_pos: tuple) -> list:
        """Calculate path based on behavior."""
        start = self.enemy.position

        if self.enemy.behavior == 'retreat':
            goal = self.find_retreat_position(player_pos)
        elif self.enemy.behavior == 'patrol':
            goal = self.find_patrol_position()
        else:  # chase
            goal = player_pos

        if goal and goal != start:
            path = a_star(start, goal, self.grid_tiles, self.enemy.mv_limit)
            return path or []
        return []

    def choose_simple_move(self, player_pos: tuple) -> tuple or None:
        """Simple move towards player if adjacent."""
        possible_Hobbies = {
            (self.enemy.position[0] + dq, self.enemy.position[1] + dr)
            for dq in [-1, 0, 1]
            for dr in [-1, 0, 1]
            if not (dq == 0 and dr == 0) and abs(dq + dr) <= 1
        }
        best_hex = None
        best_dist = float('inf')
        for hex_pos in possibile_moves:
            if hex_pos in self.grid_tiles and not self.grid_tiles[hex_pos].blocked:
                dist = hex_distance(hex_pos[0], hex_pos[1], player_pos[0], player_pos[1])
                if dist < best_dist:
                    best_dist = dist
                    best_hex = hex_pos
        return best_hex

    def find_retreat_position(self, player_pos: tuple) -> tuple or None:
        """Find hex furthest from player."""
        max_dist = 0
        best_hex = None
        for q in range(self.enemy.mv_limit):
            for r in range(self.enemy.mv_limit):
                if abs(q + r) > self.enemy.mv_limit:
                    continue
                hx, hy = self.enemy.position[0] + q, self.enemy.position[1] + r
                if (hx, hy) in self.grid_tiles and not self.grid_tiles[(hx, hy)].blocked:
                    dist = hex_distance(hx, hy, player_pos[0], player_pos[1])
                    if dist > max_dist:
                        max_dist = dist
                        best_hex = (hx, hy)
        return best_hex

    def find_patrol_position(self) -> tuple or None:
        """Find nearby unblocked hex."""
        candidates = []
        for q in range(self.enemy.mv_limit + 1):
            for r in range(self.enemy.mv_limit + 1):
                if abs(q + r) > self.enemy.mv_limit:
                    continue
                hx, hy = self.enemy.position[0] + q, self.enemy.position[1] + r
                if (hx, hy) in self.grid_tiles and not self.grid_tiles[(hx, hy)].blocked and (hx, hy) != self.enemy.position:
                    candidates.append((hx, hy))
                # Also negative
                if q > 0:
                    hx, hy = self.enemy.position[0] - q, self.enemy.position[1] + r
                    if (hx, hy) in self.grid_tiles and not self.grid_tiles[(hx, hy)].blocked and (hx, hy) != self.enemy.position:
                        candidates.append((hx, hy))
                if r > 0:
                    hx, hy = self.enemy.position[0] + q, self.enemy.position[1] - r
                    if (hx, hy) in self.grid_tiles and not self.grid_tiles[(hx, hy)].blocked and (hx, hy) != self.enemy.position:
                        candidates.append((hx, hy))
                if q > 0 and r > 0:
                    hx, hy = self.enemy.position[0] - q, self.enemy.position[1] - r
                    if (hx, hy) in self.grid_tiles and not self.grid_tiles[(hx, hy)].blocked and (hx, hy) != self.enemy.position:
                        candidates.append((hx, hy))

        if candidates:
            import random
            return random.choice(candidates)
        return None

# Note: Later integrate with Enemy.take_turn, but for now separate.
