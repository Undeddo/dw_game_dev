"""
DW Reference: Book 1, p.18-19 (terrain mods to Mv).
Purpose: Hex grid with tile generation and path viz.
Dependencies: client/map/tile.py, core/hex/utils.py, random, math.
Ext Hooks: Procedural maps from scenarios.
"""

import random
import math
from client.map.tile import Tile
from core.hex.utils import hex_distance

class HexGrid:
    def __init__(self, size=10, hex_size=50):
        self.size = size
        self.hex_size = hex_size
        self.tiles = {}  # (q, r): Tile object
        self.flat_top = True  # Flat-top hexes
        self.path_highlight = []  # Planned move path (solid yellow)
        self._initialize_grid()

    def _initialize_grid(self):
        # Generate 10x10 axial grid (q from -5 to 4, r from -5 to 4, adjust for offset)
        for q in range(-self.size // 2, self.size // 2 + 1):
            for r in range(-self.size // 2, self.size // 2 + 1):
                self.tiles[(q, r)] = Tile(random.choice(['plain'] * 8 + ['forest'] * 1 + ['wall'] * 1))  # ~10% walls, 10% forest

    def hex_to_pixel(self, q, r):
        """Convert axial coordinates to pixel position."""
        if self.flat_top:
            x = self.hex_size * 3/2 * q
            y = self.hex_size * (math.sqrt(3)/2 * q + math.sqrt(3) * r)
        else:
            x = self.hex_size * (q + 0.5 * r)
            y = self.hex_size * 1.5 * r
        return x, y

    def pixel_to_hex(self, x, y):
        """Convert pixel to axial coordinates."""
        if self.flat_top:
            # Calculate approximate axial
            x_rel = x / self.hex_size
            y_rel = y / self.hex_size
            q = (2 * x_rel) / 3
            r = (y_rel / math.sqrt(3)) - q / 2
            # Find the closest hex by checking distance to all nearby hexes
            min_dist = float('inf')
            best_q, best_r = 0, 0
            for dq in [-1, 0, 1]:
                for dr in [-1, 0, 1]:
                    cq = int(q) + dq
                    cr = int(r) + dr
                    px, py = self.hex_to_pixel(cq, cr)
                    dist = math.hypot(px - x, py - y)
                    if dist < min_dist:
                        min_dist = dist
                        best_q, best_r = cq, cr
            return best_q, best_r
        else:
            r = y / (self.hex_size * 1.5)
            q = (x - 0.5 * r * self.hex_size) / self.hex_size
            q = round(q)
            r = round(r)
            return q, r

    def set_path_highlight(self, path):
        self.path_highlight = path

    def get_grid_state(self):
        return {str(pos): tile.to_dict() for pos, tile in self.tiles.items()}
