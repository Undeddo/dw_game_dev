"""
DW Reference: Book 1, p.18-19 (terrain effects).
Purpose: Hex tiles with obstacles/costs for pathfinding.
Dependencies: None.
Ext Hooks: Add more types (e.g., water: swim roll).
Client: Visuals (colors/sprites); Server: Rules (JSON serializable).
"""

class Tile:
    def __init__(self, tile_type='plain'):
        self.type = tile_type
        if tile_type == 'plain':
            self.cost = 1
            self.blocked = False
            self.color = (0, 100, 0)  # Green
        elif tile_type == 'forest':
            self.cost = 2
            self.blocked = False
            self.color = (0, 50, 0)  # Dark green
        elif tile_type == 'wall':
            self.cost = float('inf')
            self.blocked = True
            self.color = (100, 100, 100)  # Gray
        else:
            # Default to plain
            self.cost = 1
            self.blocked = False
            self.color = (0, 100, 0)

    def get_mod(self, stat):
        # Stub for future stats mods, e.g., -1 DF for mud
        if self.type == 'mud':
            return -1
        return 0

    def to_dict(self):
        return {
            'type': self.type,
            'cost': self.cost if self.cost != float('inf') else None,
            'blocked': self.blocked
        }
