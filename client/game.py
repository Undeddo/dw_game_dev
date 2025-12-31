""" DW Reference: Book 1, p. 18-19 (exploration).
Purpose: Game loop with path queuing, smooth movement, tick sends to server.
Dependencies: client/map/hex_grid.py, client/render/character_renderer.py, utils/pathfinding.py, utils/hex_utils.py, core/config.py, pygame, requests, math.
Ext Hooks: Integrate Mv from future Stats.
Client Only: Input and visuals.

This file contains the main game loop and handles:
- Game state management
- Input handling
- Rendering
- Movement logic
- Combat system integration
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pygame
import requests
import time
import math
import threading
from client.map.hex_grid import HexGrid
from core.config import TICK_TIME, SERVER_URL, ENEMY_RANGED_ATTACK_ENABLED
from core.pathfinding.a_star import a_star
from core.hex.utils import hex_distance
from utils.draw_utils import draw_sand_clock
from utils.draw_combat_ui import draw_combat_ui
from utils.dice import roll_d6
from client.render.character_renderer import CharacterRenderer
from client.enemy import Enemy
from client.game_state import GameState
from client.ai_system import AISystem
from client.turn_based_combat_system import TurnBasedCombatSystem
from client.actors.base import ActorStats

# Initialize pygame
pygame.font.init()
font = pygame.font.SysFont('Arial', 24)
pygame.init()

class GameEngine:
    """Main game engine class that manages the game loop and all game systems."""
    
    def __init__(self):
        """Initialize the game engine with all required components."""
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
        
        # Initialize enemies with proper stats
        self.enemies = [
            Enemy(start_pos=(0, 1), mv_limit=6),
            Enemy(start_pos=(1, 3), mv_limit=6),
        ]  # Multiple enemies for more challenge
        
        # Centralize state in GameState (reduces globals; see client/game_state.py)
        self.state = GameState(
            enemies=self.enemies,  # List of Enemy instances; updates via state.enemies
            goal_pos=(9, 9),  # Quest goal hex (refs hex_grid size; per GD win condition)
            char_screen_pos=[self.SCREEN_WIDTH // 2, self.SCREEN_HEIGHT // 2],  # Screen pos
            mv_limit=6  # Default MV; exploration mode overrides to 99 per GD method
        )
        
        # Initialize combat system and AI system
        self.combat_system = TurnBasedCombatSystem(self.state, self.grid.tiles, self.grid)
        self.ai_system = AISystem(self.state, self.grid.tiles)
        
        # Debug: Check grid state (now logs use state fields)
        print(f"Grid size: {self.grid.size}, hex_size: {self.grid.hex_size}")
        print(f"Total tiles: {len(self.grid.tiles)}")
        blocked_count = sum(1 for tile in self.grid.tiles.values() if tile.blocked)
        print(f"Blocked tiles: {blocked_count}")
        print(f"Player start position: {self.state.player_pos}")
        print(f"Enemy start positions: {[enem.pos for enem in self.state.enemies]}")
        
        # Error feedback state
        self.rejected_path = []  # Hexes to flash red for rejection feedback
        self.rejected_flash_time = 0.0
        self.FLASH_DURATION = 1.0  # Seconds for red flash
        self.rejected_message = ""  # Message to display when path is rejected
        self.rejected_message_time = 0.0
        self.MESSAGE_DURATION = 3.0  # Seconds to display the message
        
        # Movement speed: 100 pixels/second, for smoother long-distance moves
        self.MOVE_SPEED = 100.0
        self.last_cr_start = time.time()
        self.attack_indicators = []  # List of (attacker_pos, victim_pos, start_time)
        
        # Game state tracking
        self.running = True
        
    def handle_input(self):
        """Handle all user input events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if self.state.defeated:
                    continue  # Dead, no movement or planning
                # Handle mouse click for path planning
                mouse_pos = pygame.mouse.get_pos()
                # Find which hex was clicked
                clicked_hex = self.grid.pixel_to_hex(mouse_pos[0], mouse_pos[1])
                if clicked_hex:
                    self._handle_path_planning(clicked_hex)
            elif event.type == pygame.KEYDOWN:
                self._handle_key_press(event.key)
    
    def _handle_path_planning(self, clicked_hex):
        """Handle path planning when player clicks on a hex."""
        # Queue path to clicked hex
        queued_path = a_star(self.state.player_pos, clicked_hex, self.grid.tiles, max_distance=self.state.mv_limit)
        if queued_path and len(queued_path) > 1:
            # Store the path in game state immediately for local use
            self.state.queued_path = queued_path
            self.state.current_path_index = 0
            self.grid.set_path_highlight(queued_path)

            # Validate path with server asynchronously
            path_data = {
                "start": self.state.player_pos,
                "end": clicked_hex,
                "mode": self.state.game_mode,
                "mv_limit": self.state.mv_limit
            }
            validation_thread = threading.Thread(target=self._validate_path_async, args=(path_data,))
            validation_thread.daemon = True
            validation_thread.start()
    
    def _handle_key_press(self, key):
        """Handle keyboard input."""
        if key == pygame.K_e:
            self.state.switch_mode('exploration')
        elif key == pygame.K_c:
            self.state.switch_mode('combat')
        elif key == pygame.K_SPACE:
            # In combat mode, SPACE ends the current turn
            if self.state.game_mode == 'combat' and not self.state.is_moving:
                self.state.switch_turn()
                self.last_cr_start = time.time()  # Reset timer
            # In other modes, SPACE cancels movement
            elif self.state.is_moving:
                self.state.is_moving = False
                self.state.queued_path = []
                self.grid.set_path_highlight([])
    
    def _validate_path_async(self, data):
        """Async validation for exploration mode."""
        try:
            resp = requests.post(f"{SERVER_URL}/api/move_path", json=data, timeout=5.0)
            if resp.status_code == 200:
                result = resp.json()
                approved_path = [tuple(p) for p in result.get("approved_path", [])]
                if approved_path:
                    print("Exploration path validated by server!")
                    # Start movement with the validated path
                    self.state.is_moving = True
                else:
                    print("Server rejected exploration path")
                    # Visual feedback
                    self.rejected_path = list(self.state.queued_path)  # Flash current path
                    self.rejected_flash_time = time.time()
                    self.rejected_message = "Path Rejected: Invalid route!"
                    self.rejected_message_time = time.time()
                    self.state.is_moving = False
                    self.state.queued_path = []
                    self.grid.set_path_highlight([])
            else:
                print("Async validation failed, continuing with local path")
                # Use the locally calculated path as fallback
                self.state.is_moving = True
        except requests.exceptions.RequestException as e:
            print(f"Async server error: {e}, continuing with local path")
            # Use the locally calculated path as fallback
            self.state.is_moving = True
    
    def update_game_state(self, dt):
        """Update all game state components."""
        # Update character renderer
        self.char_renderer.update(dt, self.state.is_moving)
        
        # Update enemy screen positions only if not currently moving (to avoid overriding LERP movement)
        for enem in self.enemies:
            if enem.hp > 0 and not enem.is_moving:
                enemy_screen_pos = self._hex_to_screen(enem.pos[0], enem.pos[1], self.grid.hex_size, self.screen)
                enem.set_screen_pos(enemy_screen_pos)
        
        # Handle rejected path flash
        if self.rejected_path and time.time() - self.rejected_flash_time < self.FLASH_DURATION:
            for hex_pos in self.rejected_path:
                if tuple(hex_pos) in self.grid.tiles and not self.grid.tiles[tuple(hex_pos)].blocked:
                    center = self.grid.hex_to_pixel(hex_pos[0], hex_pos[1])
                    cx, cy = center[0] + self.SCREEN_WIDTH // 2, center[1] + self.SCREEN_HEIGHT // 2
                    pygame.draw.circle(self.screen, (255, 0, 0), (int(cx), int(cy)), self.grid.hex_size // 2, 2)
        else:
            if self.rejected_path:
                self.rejected_path = []
        
        # Player movement in exploration mode (handled separately from combat system)
        if self.state.game_mode == 'exploration' and self.state.is_moving:
            target_hex = self.state.queued_path[self.state.current_path_index]
            target_screen = self._hex_to_screen(target_hex[0], target_hex[1], self.grid.hex_size, self.screen)
            dx = target_screen[0] - self.state.char_screen_pos[0]
            dy = target_screen[1] - self.state.char_screen_pos[1]
            dist = (dx**2 + dy**2)**0.5

            if dist < 5:  # Arrived at target hex
                self.state.char_screen_pos = [target_screen[0], target_screen[1]]
                self.state.player_pos = [target_hex[0], target_hex[1]]
                self.state.current_path_index += 1
                print(f"Player reached hex: {target_hex}")
            else:
                # LERP movement
                t = min(1.0, (self.MOVE_SPEED * dt) / dist)
                self.state.char_screen_pos[0] += dx * t
                self.state.char_screen_pos[1] += dy * t

            if self.state.current_path_index >= len(self.state.queued_path):
                self.state.is_moving = False
                self.state.queued_path = []
                self.grid.set_path_highlight([])
                # Check win condition after movement
                self.state.check_win_condition(time.time())

        # Path-following movement handled by CombatSystem for lockstep execution in combat mode
        if self.state.game_mode == 'combat':
            self.combat_system.update_positions(dt, self.grid.hex_size, self.screen, self.MOVE_SPEED)

        # Enemy path-following movement and attacks (in both exploration and combat modes)
        for enem in self.enemies:
            if enem.hp > 0:
                # Update enemy movement if they have a path
                if enem.is_moving and enem.queued_path and enem.current_path_index < len(enem.queued_path):
                    enemy_path_complete = enem.update_movement(self.grid.hex_size, self.screen, self.MOVE_SPEED, dt)
                    # Attack if path complete and within range (only in exploration mode for now)
                    if enemy_path_complete and enem.hp > 0 and self.state.game_mode == 'exploration':
                        dist = hex_distance(enem.pos[0], enem.pos[1], self.state.player_pos[0], self.state.player_pos[1])
                        if not self.state.defeated and (dist == 1 or (dist <= 3 and ENEMY_RANGED_ATTACK_ENABLED)):
                            # No more attacks on dead player
                            if dist == 1:
                                damage = roll_d6()
                                msg = f"Enemy melee attack for {damage}!"
                            else:
                                damage = max(0, roll_d6() - (dist - 1))
                                msg = f"Enemy ranged attack for {damage} (distance {dist})!"
                            if damage:
                                self.state.update_hp(damage)  # Update via GameState to sync HP
                                self.attack_indicators.append((tuple(enem.screen_pos), tuple(self.state.char_screen_pos), time.time()))
                            print(f"{msg} Player HP: {self.state.player_hp}")
        
        # Combat round tick: Execute planned actions via CombatSystem
        if self.state.game_mode == 'combat' and (time.time() - self.last_cr_start >= TICK_TIME):
            self.combat_system.execute_turn()
            self.last_cr_start = time.time()  # Reset timer

        # Enemy AI: Use AISystem for modular behavior in both modes
        if self.state.game_mode == 'exploration':
            # In exploration mode, enemies move independently with simple AI
            for enem in self.enemies:
                if enem.hp > 0 and not enem.is_moving:
                    dist = hex_distance(enem.pos[0], enem.pos[1], self.state.player_pos[0], self.state.player_pos[1])
                    # Simple chase behavior in exploration mode
                    if dist <= 5:  # Chase if within range
                        path = enem.calculate_ai_path(self.state.player_pos, self.grid.tiles, self.enemies, 'chase')
                        if path and len(path) > 0:
                            enem.start_movement(path)
        elif self.state.game_mode == 'combat':
            # Update enemy AI decisions for combat mode
            actions = self.ai_system.decide_actions_batch(self.enemies, self.state.player_pos)
            for enem, path, attack in actions:
                enem.planned_path = path
                enem.attack_this_turn = attack
    
    def _hex_to_screen(self, q, r, size, screen):
        """Convert hex coordinates to screen coordinates."""
        x = size * 3/2 * q
        y = size * math.sqrt(3) * (r + q/2)
        return (int(x + screen.get_width() // 2), int(y + screen.get_height() // 2))
    
    def draw(self):
        """Draw all game elements to the screen."""
        self.screen.fill((0, 0, 0))
        self.grid.draw(self.screen)
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
                enem.draw(self.screen, 0)  # dt parameter not needed here
        
        # Draw health bars (now pulls from state with ActorStats backing)
        self._draw_health_bar(self.screen, int(self.state.char_screen_pos[0]), int(self.state.char_screen_pos[1]), 
                             self.state.player_hp, self.state.max_player_hp)
        for enem in self.enemies:
            if enem.hp > 0:
                self._draw_health_bar(self.screen, int(enem.screen_pos[0]), int(enem.screen_pos[1]), 
                                     enem.hp, enem.max_hp)
        
        # Draw attack indicators
        current_time = time.time()
        for attacker_pos, victim_pos, start_time in self.attack_indicators.copy():
            if current_time - start_time > 5:
                self.attack_indicators.remove((attacker_pos, victim_pos, start_time))
            else:
                # Check if this is an enemy attack (based on position matching an enemy)
                is_enemy_attack = False
                for enem in self.enemies:
                    if enem.hp > 0 and tuple(enem.screen_pos) == attacker_pos:
                        is_enemy_attack = True
                        enem.renderer.draw_attack_arrow(self.screen, attacker_pos, victim_pos, color=(255, 100, 100))
                        break
                # If not an enemy attack, draw with default method
                if not is_enemy_attack:
                    self._draw_attack_arrow(self.screen, attacker_pos, victim_pos, color=(200, 200, 200))
        
        # Draw quest goal star (yellow polygon; references hex_to_screen)
        goal_screen = self._hex_to_screen(self.state.goal_pos[0], self.state.goal_pos[1], self.grid.hex_size, self.screen)
        pygame.draw.polygon(self.screen, (255, 255, 0), [
            # Yellow star for goal
            (goal_screen[0], goal_screen[1] - 15),
            (goal_screen[0] + 6, goal_screen[1] - 5),
            (goal_screen[0] + 15, goal_screen[1] + 2),
            (goal_screen[0] + 6, goal_screen[1] + 9),
            (goal_screen[0], goal_screen[1] + 15),
            (goal_screen[0] - 6, goal_screen[1] + 9),
            (goal_screen[0] - 15, goal_screen[1] + 2),
            (goal_screen[0] - 6, goal_screen[1] - 5),
        ])
        
        # Draw combat sand clock and round counter
        if self.state.game_mode == 'combat':
            clock_x, clock_y = self.SCREEN_WIDTH - 60, 60  # Top-right corner
            size = 30  # Size of hourglass
            elapsed = min(TICK_TIME, time.time() - self.last_cr_start)
            progress = elapsed / TICK_TIME
            draw_sand_clock(self.screen, clock_x, clock_y, size, progress, font, self.state.combat_round)
        
        # Draw combat UI (HP bars, engagement highlights; references draw_sand_clock for consistent draw order)
        # Commented out for multiple enemies - need to update the UI to handle list
        # draw_combat_ui(screen, font, player_hp, 10, enemy.hp, enemy_max_hp, tuple(char_pos), tuple(enemy.pos), tuple(char_screen_pos), tuple(enemy.screen_pos))
        
        # Draw rejected message if active
        if self.rejected_message and (time.time() - self.rejected_message_time < self.MESSAGE_DURATION):
            rejected_text_surface = font.render(self.rejected_message, True, (255, 0, 0))  # Red text
            text_rect = rejected_text_surface.get_rect(center=(self.SCREEN_WIDTH // 2, self.SCREEN_HEIGHT // 2 + 100))
            self.screen.blit(rejected_text_surface, text_rect)
        
        # Draw win message if active (references rejected_message display)
        if self.state.win_message and (time.time() - self.state.win_message_time < self.state.WIN_DURATION):
            win_text_surface = font.render(self.state.win_message, True, (0, 255, 0))  # Green text
            text_rect = win_text_surface.get_rect(center=(self.SCREEN_WIDTH // 2, self.SCREEN_HEIGHT // 2 - 150))
            self.screen.blit(win_text_surface, text_rect)
        
        # Draw tutorial text
        mode_text = font.render(f"Mode: {self.state.game_mode} (E: exploration, C: combat)", True, (255, 255, 255))
        self.screen.blit(mode_text, (10, 10))
        
        # Show whose turn it is in combat mode
        if self.state.game_mode == 'combat':
            turn_text = font.render(f"Turn: {self.state.current_turn.capitalize()}", True, (255, 255, 255))
            self.screen.blit(turn_text, (10, 30))
            tutorial_text = font.render("Left-click a hex to queue movement. Press SPACE to end turn.", True, (255, 255, 255))
            self.screen.blit(tutorial_text, (10, 50))
        else:
            tutorial_text = font.render("Left-click a hex to queue movement. Server validates on click and starts movement if approved.", True, (255, 255, 255))
            self.screen.blit(tutorial_text, (10, 30))
        quit_text = font.render("Close window to quit. Server logs moves.", True, (255, 255, 255))
        self.screen.blit(quit_text, (10, 50))
    
    def _draw_health_bar(self, screen, x, y, current, max_hp, width=50, height=5):
        """Draw a health bar on the screen."""
        bar_x = x - width // 2
        bar_y = y - 50
        pygame.draw.rect(screen, (255, 0, 0), (bar_x, bar_y, width, height))  # Red bg
        if max_hp > 0:
            current_clamped = max(0, current)  # Clamp to 0 visually to hide bar on death
            health_pct = min(1, current_clamped / max_hp)
            pygame.draw.rect(screen, (0, 255, 0), (bar_x, bar_y, width * health_pct, height))  # Green fg
    
    def _draw_attack_arrow(self, screen, attacker_pos, victim_pos, color=(255, 255, 255)):
        """Draw an attack arrow on the screen."""
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
    
    def run(self):
        """Main game loop."""
        while self.running:
            dt = self.clock.tick(60) / 1000.0  # Delta time
            
            # Handle input
            self.handle_input()
            
            # Update game state
            self.update_game_state(dt)
            
            # Draw everything
            self.draw()
            
            # Update display
            pygame.display.flip()
        
        # End of game loop
        pygame.quit()

def main():
    """Main entry point for the game."""
    game = GameEngine()
    game.run()

if __name__ == "__main__":
    main()
