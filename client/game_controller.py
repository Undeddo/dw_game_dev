"""
DW Reference: Book 1, p. 18-19 (exploration).
Purpose: Main game controller managing game flow and state.
Dependencies: client/map/hex_grid.py, client/render/character_renderer.py, utils/pathfinding.py, utils/hex_utils.py, core/config.py, pygame, requests, math.
Ext Hooks: Integrate Mv from future Stats.
Client Only: Input and visuals.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pygame
import time
import threading
from client.map.hex_grid import HexGrid
from core.config import TICK_TIME, SERVER_URL, ENEMY_RANGED_ATTACK_ENABLED
from core.pathfinding.a_star import a_star
from core.hex.utils import hex_distance
from utils.draw_utils import draw_sand_clock
from utils.dice import roll_d6
from client.render.character_renderer import CharacterRenderer
from client.enemy import Enemy
from client.game_state import GameState
from client.ai_system import AISystem
from client.combat_system import CombatSystem
from client.input_handler import InputHandler

class GameController:
    """
    Main game controller that manages the overall game flow and state.
    Handles initialization, game loop, and coordination between subsystems.
    """
    
    def __init__(self):
        """Initialize the game controller and all subsystems."""
        # Initialize Pygame
        pygame.init()
        pygame.font.init()
        self.font = pygame.font.SysFont('Arial', 24)
        
        # Screen setup
        self.SCREEN_WIDTH = 1024
        self.SCREEN_HEIGHT = 768
        self.screen = pygame.display.set_mode((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
        pygame.display.set_caption("Dragon Warriors - Exploration")
        
        # Clock for maintaining FPS
        self.clock = pygame.time.Clock()
        
        # Game objects
        self.grid = HexGrid(size=10, hex_size=50)
        self.char_renderer = CharacterRenderer()
        self.enemies = [
            Enemy(start_pos=(0, 1), mv_limit=6),
            Enemy(start_pos=(1, 3), mv_limit=6),
        ]
        
        # Centralize state in GameState (reduces globals; see client/game_state.py)
        self.state = GameState(
            enemies=self.enemies,
            goal_pos=(9, 9),
            char_screen_pos=[self.screen.get_width() // 2, self.screen.get_height() // 2],
            mv_limit=6
        )
        
        self.combat_system = CombatSystem(self.state, self.grid.tiles, self.grid)
        self.ai_system = AISystem(self.state, self.grid.tiles)
        self.input_handler = InputHandler(self.state, self.grid)
        
        # Movement speed: 100 pixels/second, for smoother long-distance moves
        self.MOVE_SPEED = 100.0
        self.last_cr_start = time.time()
        
        # Error feedback state
        self.rejected_path = []
        self.rejected_flash_time = 0.0
        self.FLASH_DURATION = 1.0
        
        self.rejected_message = ""
        self.rejected_message_time = 0.0
        self.MESSAGE_DURATION = 3.0
        
        self.attack_indicators = []
        self.last_auto_attack = 0.0
        
        # Debug: Check grid state (now logs use state fields)
        print(f"Grid size: {self.grid.size}, hex_size: {self.grid.hex_size}")
        print(f"Total tiles: {len(self.grid.tiles)}")
        blocked_count = sum(1 for tile in self.grid.tiles.values() if tile.blocked)
        print(f"Blocked tiles: {blocked_count}")
        print(f"Player start position: {self.state.player_pos}")
        print(f"Enemy start positions: {[enem.pos for enem in self.state.enemies]}")
        
        self.running = True
    
    def handle_events(self):
        """Handle all game events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self.input_handler.handle_mouse_click(event.pos, self.state, self.grid, self.enemies)
            elif event.type == pygame.KEYDOWN:
                self.input_handler.handle_keydown(event.key, self.state, self.grid)
    
    def update(self, dt, current_time):
        """Update game state."""
        # Update character renderer
        self.char_renderer.update(dt, self.state.is_moving)
        
        # Update enemy screen positions only if not currently moving
        for enem in self.enemies:
            if enem.hp > 0 and not enem.is_moving:
                enemy_screen_pos = self.grid.hex_to_pixel(enem.pos[0], enem.pos[1])
                # Convert to screen coordinates
                screen_x = enemy_screen_pos[0] + self.screen.get_width() // 2
                screen_y = enemy_screen_pos[1] + self.screen.get_height() // 2
                enem.set_screen_pos((screen_x, screen_y))
        
        # Update combat system positions
        self.combat_system.update_positions(dt, self.grid.hex_size, self.screen, self.MOVE_SPEED)
        
        # Handle enemy attacks and movement
        self._handle_enemy_attacks_and_movement(current_time)
        
        # Handle combat round tick
        self._handle_combat_round_tick(current_time)
        
        # Update AI if in combat mode
        self._update_ai(current_time)
        
        # Check win condition
        self.state.check_win_condition(current_time)
    
    def _handle_enemy_attacks_and_movement(self, current_time):
        """Handle enemy attacks and movement after path completion."""
        for enem in self.enemies:
            if enem.hp > 0:
                # Update enemy movement if they have a path
                if enem.is_moving and enem.queued_path and enem.current_path_index < len(enem.queued_path):
                    enemy_path_complete = enem.update_movement(self.grid.hex_size, self.screen, self.MOVE_SPEED, self.clock.get_time() / 1000.0)
                    
                    # Attack if path complete and within range
                    if enemy_path_complete and enem.hp > 0:
                        dist = hex_distance(enem.pos[0], enem.pos[1], self.state.player_pos[0], self.state.player_pos[1])
                        if not self.state.defeated and (dist == 1 or (dist <= 3 and ENEMY_RANGED_ATTACK_ENABLED)):
                            if dist == 1:
                                damage = roll_d6()
                                msg = f"Enemy melee attack for {damage}!"
                            else:
                                damage = max(0, roll_d6() - (dist - 1))
                                msg = f"Enemy ranged attack for {damage} (distance {dist})!"
                            if damage:
                                self.state.update_hp(damage)
                                self.attack_indicators.append((tuple(enem.screen_pos), tuple(self.state.char_screen_pos), current_time))
                                print(f"{msg} Player HP: {self.state.player_hp}")
    
    def _handle_combat_round_tick(self, current_time):
        """Handle combat round ticks for lockstep execution."""
        if self.state.game_mode == 'combat' and (current_time - self.last_cr_start >= TICK_TIME):
            self.combat_system.execute_round_tick()
            self.last_cr_start = current_time
    
    def _update_ai(self, current_time):
        """Update AI behavior if in combat mode."""
        if self.state.game_mode == 'combat':
            # Pass player HP directly as it's accessed as a property
            self.ai_system.update_ai(self.enemies, self.state.player_pos)
    
    def draw(self, current_time):
        """Draw the entire game state."""
        self.screen.fill((0, 0, 0))
        self.grid.draw(self.screen)
        
        # Draw character
        self.char_renderer.draw_character(self.screen, int(self.state.char_screen_pos[0]), int(self.state.char_screen_pos[1]))
        
        # Draw death overlay if player is dead
        if self.state.defeated:
            dead_overlay = pygame.Surface((32, 32))
            dead_overlay.fill((100, 100, 100))
            dead_overlay.set_alpha(150)
            self.screen.blit(dead_overlay, (int(self.state.char_screen_pos[0] - 16), int(self.state.char_screen_pos[1] - 16)))
        
        # Draw enemies
        for enem in self.enemies:
            if enem.hp > 0:
                enem.draw(self.screen, self.clock.get_time() / 1000.0)
        
        # Draw health bars
        self._draw_health_bars()
        
        # Draw attack indicators
        self._draw_attack_indicators(current_time)
        
        # Draw quest goal star
        self._draw_goal_star()
        
        # Draw combat UI if in combat mode
        if self.state.game_mode == 'combat':
            self._draw_combat_ui(current_time)
        
        # Draw rejected message if active
        self._draw_rejected_message(current_time)
        
        # Draw win message if active
        self._draw_win_message(current_time)
        
        # Draw tutorial text
        self._draw_tutorial_text()
        
        pygame.display.flip()
    
    def _draw_health_bars(self):
        """Draw health bars for player and enemies."""
        from utils.draw_utils import draw_health_bar
        
        # Draw player health bar
        draw_health_bar(self.screen, int(self.state.char_screen_pos[0]), int(self.state.char_screen_pos[1]), 
                       self.state.player_hp, self.state.max_player_hp)
        
        # Draw enemy health bars
        for enem in self.enemies:
            if enem.hp > 0:
                draw_health_bar(self.screen, int(enem.screen_pos[0]), int(enem.screen_pos[1]), 
                               enem.hp, enem.max_hp)
    
    def _draw_attack_indicators(self, current_time):
        """Draw attack indicators."""
        for attacker_pos, victim_pos, start_time in self.attack_indicators.copy():
            if current_time - start_time > 5:
                self.attack_indicators.remove((attacker_pos, victim_pos, start_time))
            else:
                # Check if this is an enemy attack
                is_enemy_attack = False
                for enem in self.enemies:
                    if enem.hp > 0 and tuple(enem.screen_pos) == attacker_pos:
                        is_enemy_attack = True
                        enem.renderer.draw_attack_arrow(self.screen, attacker_pos, victim_pos, color=(255, 100, 100))
                        break
                
                # If not an enemy attack, draw with default method
                if not is_enemy_attack:
                    self._draw_attack_arrow(self.screen, attacker_pos, victim_pos, color=(200, 200, 200))
    
    def _draw_attack_arrow(self, screen, attacker_pos, victim_pos, color=(255, 255, 255)):
        """Draw a simple attack arrow."""
        import math
        pygame.draw.line(screen, color, attacker_pos, victim_pos, 3)
        dx = victim_pos[0] - attacker_pos[0]
        dy = victim_pos[1] - attacker_pos[1]
        length = math.hypot(dx, dy)
        if length == 0:
            return
        dx /= length
        dy /= length
        arrow_tip = victim_pos
        p1 = (arrow_tip[0] - dx * 10 - dy * 5, arrow_tip[1] - dy * 10 + dx * 5)
        p2 = (arrow_tip[0] - dx * 10 + dy * 5, arrow_tip[1] - dy * 10 - dx * 5)
        pygame.draw.polygon(screen, color, [arrow_tip, p1, p2])
    
    def _draw_goal_star(self):
        """Draw the quest goal star."""
        goal_screen = self.grid.hex_to_pixel(self.state.goal_pos[0], self.state.goal_pos[1])
        # Convert to screen coordinates
        screen_x = goal_screen[0] + self.screen.get_width() // 2
        screen_y = goal_screen[1] + self.screen.get_height() // 2
        
        pygame.draw.polygon(self.screen, (255, 255, 0), [  # Yellow star for goal
            (screen_x, screen_y - 15),
            (screen_x + 6, screen_y - 5),
            (screen_x + 15, screen_y + 2),
            (screen_x + 6, screen_y + 9),
            (screen_x, screen_y + 15),
            (screen_x - 6, screen_y + 9),
            (screen_x - 15, screen_y + 2),
            (screen_x - 6, screen_y - 5),
        ])
    
    def _draw_combat_ui(self, current_time):
        """Draw combat UI elements."""
        clock_x, clock_y = self.SCREEN_WIDTH - 60, 60  # Top-right corner
        size = 30  # Size of hourglass
        elapsed = min(TICK_TIME, current_time - self.last_cr_start)
        progress = elapsed / TICK_TIME
        draw_sand_clock(self.screen, clock_x, clock_y, size, progress, self.font, self.state.combat_round)
    
    def _draw_rejected_message(self, current_time):
        """Draw rejected path message."""
        if self.rejected_message and (current_time - self.rejected_message_time < self.MESSAGE_DURATION):
            rejected_text_surface = self.font.render(self.rejected_message, True, (255, 0, 0)) # Red text
            text_rect = rejected_text_surface.get_rect(center=(self.SCREEN_WIDTH // 2, self.SCREEN_HEIGHT // 2 + 100))
            self.screen.blit(rejected_text_surface, text_rect)
    
    def _draw_win_message(self, current_time):
        """Draw win/lose message."""
        if self.state.win_message and (current_time - self.state.win_message_time < self.state.WIN_DURATION):
            win_text_surface = self.font.render(self.state.win_message, True, (0, 255, 0)) # Green text
            text_rect = win_text_surface.get_rect(center=(self.SCREEN_WIDTH // 2, self.SCREEN_HEIGHT // 2 - 150))
            self.screen.blit(win_text_surface, text_rect)
    
    def _draw_tutorial_text(self):
        """Draw tutorial text."""
        mode_text = self.font.render(f"Mode: {self.state.game_mode} (E: exploration, C: combat)", True, (255, 255, 255))
        self.screen.blit(mode_text, (10, 10))
        tutorial_text = self.font.render("Left-click a hex to queue movement. Server validates on click and starts movement if approved.", True, (255, 255, 255))
        self.screen.blit(tutorial_text, (10, 30))
        quit_text = self.font.render("Close window to quit. Server logs moves.", True, (255, 255, 255))
        self.screen.blit(quit_text, (10, 50))
    
    def run(self):
        """Main game loop."""
        while self.running:
            dt = self.clock.tick(60) / 1000.0  # Delta time
            current_time = time.time()
            
            self.handle_events()
            self.update(dt, current_time)
            self.draw(current_time)
        
        pygame.quit()
