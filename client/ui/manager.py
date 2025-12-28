"""
DW Reference: Book 1, p.80-82 (HP bars, timers).
Purpose: UIManager for messages, health bars, sand-clock in combat.
Dependencies: pygame, core.config, utils.draw_utils, utils.draw_combat_ui.
Client Only: UI drawing abstraction.
"""

import pygame
from core.config import FONT, WIN_DURATION, MESSAGE_DURATION
from utils.draw_utils import draw_sand_clock
from utils.draw_combat_ui import draw_hp_bar, draw_combat_ui
from typing import Tuple

class UIManager:
    def __init__(self, font):
        self.font = font

    def draw_health_bar(self, screen: pygame.Surface, x, y, current, max_hp, color=(255, 0, 0), width=50, height=5):
        draw_hp_bar(screen, x, y, current, max_hp, color, width, height)

    def draw_combat_ui(self, screen: pygame.Surface, player_hp, player_max_hp, enemies, player_pos, player_screen_pos):
        """
        Draw combat UI elements including health bars and engagement highlights.
        - player_hp: Current player HP.
        - player_max_hp: Maximum player HP.
        - enemies: List of enemy objects.
        - player_pos: Player's position in hex coordinates.
        - player_screen_pos: Player's position in screen coordinates.
        """
        # Draw player health bar
        self.draw_health_bar(screen, player_screen_pos[0], player_screen_pos[1], player_hp, player_max_hp, color=(0, 255, 0))
        
        # Draw enemy health bars
        for enemy in enemies:
            if enemy.hp > 0:
                self.draw_health_bar(screen, enemy.screen_pos[0], enemy.screen_pos[1], enemy.hp, enemy.max_hp, color=(255, 0, 0))

    def draw_sand_clock(self, screen: pygame.Surface, clock_x, clock_y, size, progress, combat_round):
        draw_sand_clock(screen, clock_x, clock_y, size, progress, self.font, combat_round)

    def draw_message(self, screen: pygame.Surface, message: str, color: Tuple[int, int, int], pos: Tuple[int, int]):
        text_surface = self.font.render(message, True, color)
        screen.blit(text_surface, pos)

    def draw_win_message(self, screen: pygame.Surface, message: str, time_shown: float, current_time: float, pos: Tuple[int, int]):
        if current_time - time_shown < WIN_DURATION:
            self.draw_message(screen, message, (0, 255, 0), pos)

    def draw_rejected_message(self, screen: pygame.Surface, message: str, time_shown: float, current_time: float, pos: Tuple[int, int]):
        if current_time - time_shown < MESSAGE_DURATION:
            self.draw_message(screen, message, (255, 0, 0), pos)

    def draw_combat_message(self, screen: pygame.Surface, message: str, time_shown: float, current_time: float, pos: Tuple[int, int]):
        if current_time - time_shown < MESSAGE_DURATION:
            self.draw_message(screen, message, (255, 255, 0), pos)

# Usage: ui = UIManager(font); ui.draw_health_bar(screen, x, y, hp, 10)
