"""
DW Reference: Book 1, p.80-82 (hits, HP).
Purpose: Utility functions to draw combat UI elements: HP bars, engagement highlights.
Dependencies: pygame, utils.hex_utils for distance checks.
Ext Hooks: Expand to more stats (e.g., armor, weapons later).
Client Only: Visual overlays for combat.
Grand Scheme: Granular utils for combat visuals, keeping game.py lean (import and call in draw loop).
"""

import pygame
from utils.hex_utils import hex_distance

def is_engaged(player_hex, enemy_hex):
    """
    Check if player and enemy are adjacent (engaged for attacks, DW engagement rules).
    - References: hex_distance in utils/hex_utils for adjacency check.
    - Purpose: Determines combat UI highlights and attack opportunities.
    """
    dist = hex_distance(player_hex[0], player_hex[1], enemy_hex[0], enemy_hex[1])
    return dist == 1

def draw_hp_bar(screen, x, y, current_hp, max_hp, color=(255, 0, 0), bar_width=40, bar_height=6):
    """
    Draw a simple HP bar above entity (references pygame draws in draw_utils.py).
    - References: pygame.draw.rect for bars, similar to sand_clock fills.
    - Purpose: Visual HP feedback during combat.
    """
    pygame.draw.rect(screen, (0, 0, 0), (x - bar_width // 2, y - 20, bar_width, bar_height), 1)
    hp_ratio = current_hp / max_hp
    pygame.draw.rect(screen, color, (x - bar_width // 2, y - 20, int(bar_width * hp_ratio), bar_height))

def draw_combat_ui(screen, font, player_hp, player_max_hp, enemy_hp, enemy_max_hp, player_hex, enemy_hex, player_screen_pos, enemy_screen_pos):
    """
    Draw combat UI: HP bars if engaged, highlights for engagement.
    - References: is_engaged for adjacency, draw_hp_bar for visuals.
    - Purpose: Add visual appeal and info to combat, called in game.py draw section when mode='combat'.
    """
    engaged = is_engaged(player_hex, enemy_hex)
    if not engaged:
        return

    # Draw HP bars for player and enemy (above entities)
    player_x, player_y = player_screen_pos
    draw_hp_bar(screen, player_x, player_y, player_hp, player_max_hp, color=(0, 255, 0))  # Green for player

    enemy_x, enemy_y = enemy_screen_pos
    draw_hp_bar(screen, enemy_x, enemy_y, enemy_hp, enemy_max_hp, color=(255, 0, 0))  # Red for enemy

    # Flash engagement highlight (translucent red circle on adjacent hexes, references grid flash in game.py)
    for pos in [player_hex, enemy_hex]:
        center = (enemy_x if pos == enemy_hex else player_x, enemy_y if pos == enemy_hex else player_y)  # Approximate
        pygame.draw.circle(screen, (255, 128, 128), center, 20, 0)  # Semi-transparent red for intensity
