"""
DW Reference: Book 1, p.18-19 (terrain mods to Mv).
Purpose: Hex grid drawing and visuals.
Dependencies: core/hex/grid.py, client/map/tile.py, core/hex/utils.py, pygame, random, math.
Ext Hooks: Procedural maps from scenarios.
Client Only: Visuals.
"""

import pygame
import random
import math  # For trigonometry
from core.hex.grid import HexGrid as HexGridCore
from client.map.tile import Tile
from core.hex.utils import hex_distance

class HexGrid(HexGridCore):
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
