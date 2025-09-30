"""
DW Reference: Book 1, p.18-19 (terrain mods to Mv).
<<<<<<< HEAD
Purpose: Hex grid drawing and visuals.
Dependencies: core/hex/grid.py, client/map/tile.py, core/hex/utils.py, pygame, random, math.
=======
Purpose: Hex grid with tile generation, drawing, and path viz.
Dependencies: client/map/tile.py, utils/hex_utils.py, pygame, random.
>>>>>>> ee48eee (initial commit - existing game files)
Ext Hooks: Procedural maps from scenarios.
Client Only: Visuals.
"""

import pygame
import random
import math  # For trigonometry
<<<<<<< HEAD
from core.hex.grid import HexGrid as HexGridCore
from client.map.tile import Tile
from core.hex.utils import hex_distance

class HexGrid(HexGridCore):
=======
from client.map.tile import Tile
from utils.hex_utils import hex_distance

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

>>>>>>> ee48eee (initial commit - existing game files)
    def get_hex_at_mouse(self, pos, screen):
        x, y = pos
        x -= screen.get_width() // 2
        y -= screen.get_height() // 2
        q, r = self.pixel_to_hex(x, y)
        return q, r

    def draw_hex(self, screen, q, r, color=None):
        center = self.hex_to_pixel(q, r)
        cx, cy = center[0] + screen.get_width() // 2, center[1] + screen.get_height() // 2  # Center on screen
        size = self.hex_size
        points = []
        for i in range(6):
            angle_deg = 60 * i if self.flat_top else 60 * i + 30
            angle_rad = math.radians(angle_deg)
            px = cx + size * math.cos(angle_rad)
            py = cy + size * math.sin(angle_rad)
            points.append((px, py))
        if not color:
            if (q, r) in self.tiles:
                color = self.tiles[(q, r)].color
            else:
                color = (0, 100, 0)  # Default green
        pygame.draw.polygon(screen, color, points)
        pygame.draw.lines(screen, (0, 0, 0), True, points, 1)

<<<<<<< HEAD
=======
    def set_path_highlight(self, path):
        self.path_highlight = path

    def get_grid_state(self):
        return {str(pos): tile.to_dict() for pos, tile in self.tiles.items()}

>>>>>>> ee48eee (initial commit - existing game files)
    def draw_highlight_path(self, screen, path, color, alpha=128):
        """Draw a path with specified color and alpha."""
        if not path:
            return

        for pos in path:
            pos_tuple = tuple(pos)  # Ensure tuple for dict lookup
            if pos_tuple in self.tiles and not self.tiles[pos_tuple].blocked:
                center = self.hex_to_pixel(pos_tuple[0], pos_tuple[1])
                cx, cy = center[0] + screen.get_width() // 2, center[1] + screen.get_height() // 2
                size = self.hex_size
                points = []
                for i in range(6):
                    angle_deg = 60 * i if self.flat_top else 60 * i + 30
                    angle_rad = math.radians(angle_deg)
                    px = cx + size * math.cos(angle_rad)
                    py = cy + size * math.sin(angle_rad)
                    points.append((px, py))

                # Draw semi-transparent overlay
                surf_width = int(size * 3.5)
                surf_height = int(size * 3.5)
                temp_surf = pygame.Surface((surf_width, surf_height), pygame.SRCALPHA)
                temp_surf_points = [(p[0] - cx + surf_width//2, p[1] - cy + surf_height//2) for p in points]
                pygame.draw.polygon(temp_surf, color + (alpha,), temp_surf_points)
                screen.blit(temp_surf, (cx - surf_width//2, cy - surf_height//2))

    def draw(self, screen):
        for q, r in self.tiles:
            self.draw_hex(screen, q, r)

        # Draw planned move path (solid)
        self.draw_highlight_path(screen, self.path_highlight, (255, 255, 0), 128)
