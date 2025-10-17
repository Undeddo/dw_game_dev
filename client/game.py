"""
DW Reference: Book 1, p. 18-19 (exploration).
Purpose: Game loop with path queuing, smooth movement, tick sends to server.
Dependencies: client/map/hex_grid.py, client/render/character_renderer.py, utils/pathfinding.py, utils/hex_utils.py, core/config.py, pygame, requests, math.
Ext Hooks: Integrate Mv from future Stats.
Client Only: Input and visuals.
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
# TICK_TIME = 1.0  # Commented out; using config for production
from core.pathfinding.a_star import a_star
from core.hex.utils import hex_distance
from utils.draw_utils import draw_sand_clock
from utils.draw_combat_ui import draw_combat_ui
from utils.dice import roll_d6
from client.render.character_renderer import CharacterRenderer
from client.enemy import Enemy
from client.game_state import GameState
from client.ai_system import AISystem
from client.combat_system import CombatSystem

pygame.font.init()
font = pygame.font.SysFont('Arial', 24)

pygame.init()

# Screen setup
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Dragon Warriors - Exploration")

# Clock for maintaining FPS
clock = pygame.time.Clock()

# Game objects
grid = HexGrid(size=10, hex_size=50)
char_renderer = CharacterRenderer()
enemies = [
    Enemy(start_pos=(0, 1), mv_limit=6),
    Enemy(start_pos=(1, 3), mv_limit=6),
]  # Multiple enemies for more challenge

# Centralize state in GameState (reduces globals; see client/game_state.py)
state = GameState(
    enemies=enemies,  # List of Enemy instances; updates via state.enemies
    goal_pos=(9, 9),  # Quest goal hex (refs hex_grid size; per GD win condition)
    char_screen_pos=[screen.get_width() // 2, screen.get_height() // 2],  # Screen pos
    mv_limit=6  # Default MV; exploration mode overrides to 99 per GD method
)
combat_system = CombatSystem(state, grid.tiles, grid)  # Initialized combat system
ai_system = AISystem(state, grid.tiles)  # Manage AI separately; reduces spam in main loop
char_pos = state.player_pos  # Alias for legacy refs; will remove in Step 2
game_mode = state.game_mode  # Alias; will remove
player_hp = state.player_hp  # Alias via @property; remove when full migration
goal_pos = state.goal_pos  # Alias; will remove
char_screen_pos = state.char_screen_pos  # Alias; will remove
queued_path = state.queued_path  # Alias; will remove
is_moving = state.is_moving  # Alias; will remove
path_validated = state.path_validated  # Alias; will remove
server_offline = state.server_offline  # Alias; will remove
combat_round = state.combat_round  # Alias; will remove
win_message = state.win_message  # Alias; will remove
win_message_time = state.win_message_time  # Alias; will remove
last_auto_attack = state.last_auto_attack  # Alias; will remove


# Debug: Check grid state (now logs use state fields)
print(f"Grid size: {grid.size}, hex_size: {grid.hex_size}")
print(f"Total tiles: {len(grid.tiles)}")
blocked_count = sum(1 for tile in grid.tiles.values() if tile.blocked)
print(f"Blocked tiles: {blocked_count}")
print(f"Player start position: {state.player_pos}")
print(f"Enemy start positions: {[enem.pos for enem in state.enemies]}")

# Error feedback state
rejected_path = []  # Hexes to flash red for rejection feedback
rejected_flash_time = 0.0
FLASH_DURATION = 1.0  # Seconds for red flash

rejected_message = "" # Message to display when path is rejected
rejected_message_time = 0.0
MESSAGE_DURATION = 3.0 # Seconds to display the message



# Movement speed: 100 pixels/second, for smoother long-distance moves
MOVE_SPEED = 100.0
last_start_time = time.time()
last_cr_start = time.time()
combat_round = 0
planned_path = None
attack_indicators = []  # List of (attacker_pos, victim_pos, start_time)
last_auto_attack = 0.0  # Timestamp for last auto attack by player

def validate_path_async(data):
    """Async validation for exploration mode."""
    global path_validated, is_moving, rejected_path, rejected_flash_time
    try:
        resp = requests.post(f"{SERVER_URL}/api/move_path", json=data, timeout=5.0)
        if resp.status_code == 200:
            result = resp.json()
            approved_path = [tuple(p) for p in result.get("approved_path", [])]
            if approved_path:
                path_validated = True
                print("Exploration path validated by server!")
            else:
                print("Server rejected exploration path, stopping movement")
                # Visual feedback
                global rejected_message, rejected_message_time
                rejected_path = list(queued_path)  # Flash current path
                rejected_flash_time = time.time()
                rejected_message = "Path Rejected: Invalid route!"
                rejected_message_time = time.time()
                is_moving = False
                queued_path = []
                grid.set_path_highlight([])
        else:
            print("Async validation failed, continuing with local path")
            path_validated = True
    except requests.exceptions.RequestException as e:
        print(f"Async server error: {e}, continuing with local path")
        path_validated = True


def validate_combat_path_async(path, data):
    """Async validation for combat mode."""
    global planned_path, rejected_path, rejected_flash_time, rejected_message, rejected_message_time
    try:
        resp = requests.post(f"{SERVER_URL}/api/move_path", json=data, timeout=5.0)
        if resp.status_code == 200:
            result = resp.json()
            approved_path = [tuple(p) for p in result.get("approved_path", [])]
            if approved_path:
                if planned_path is not None and approved_path != planned_path:
                    grid.set_path_highlight(approved_path)
                    planned_path = approved_path
                    print("Combat path approved, updated.")
            else:
                print("Combat path rejected by server")
                # Visual feedback: clear highlight, flash red
                rejected_path = path
                rejected_flash_time = time.time()
                rejected_message = "Path Rejected!"
                rejected_message_time = time.time()
                grid.set_path_highlight([])
                planned_path = None
        else:
            print("Combat validation failed")
            # Treat as rejected
            rejected_path = path
            rejected_flash_time = time.time()
            rejected_message = "Validation Failed!"
            rejected_message_time = time.time()
            grid.set_path_highlight([])
            planned_path = None
    except requests.exceptions.RequestException as e:
        print(f"Combat server error: {e}, keeping local path")
        # Keep local planned_path and highlight
        pass


def hex_to_screen(q, r, size, screen):
    x = size * 3/2 * q
    y = size * math.sqrt(3) * (r + q/2)
    return (int(x + screen.get_width() // 2), int(y + screen.get_height() // 2))


def get_closest_enemy(char_pos, enemies):
    closest = None
    min_dist = float('inf')
    for enem in enemies:
        dist = hex_distance(char_pos[0], char_pos[1], enem.pos[0], enem.pos[1])
        if dist < min_dist and enem.hp > 0:
            min_dist = dist
            closest = enem
    return closest


def draw_health_bar(screen, x, y, current, max_hp, width=50, height=5):
    bar_x = x - width // 2
    bar_y = y - 50
    pygame.draw.rect(screen, (255, 0, 0), (bar_x, bar_y, width, height))  # Red bg
    if max_hp > 0:
        current_clamped = max(0, current)  # Clamp to 0 visually to hide bar on death
        health_pct = min(1, current_clamped / max_hp)
        pygame.draw.rect(screen, (0, 255, 0), (bar_x, bar_y, width * health_pct, height))  # Green fg


def draw_attack_arrow(screen, attacker_pos, victim_pos, color=(255, 255, 255)):
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



running = True
while running:
    dt = clock.tick(60) / 1000.0  # Delta time
    current_time = time.time()

    char_renderer.update(dt, is_moving)

    # Update enemy screen positions only if not currently moving (to avoid overriding LERP movement)
    for enem in enemies:
        if enem.hp > 0 and not enem.is_moving:
            enemy_screen_pos = hex_to_screen(enem.pos[0], enem.pos[1], grid.hex_size, screen)
            enem.set_screen_pos(enemy_screen_pos)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if state.defeated:
                continue  # Dead, no movement or planning
            mouse_pos = pygame.mouse.get_pos()
            goal = grid.get_hex_at_mouse(mouse_pos, screen)
            if goal:
                # Handle based on mode
                if game_mode == 'exploration':
                    # Exploration: switch path without interruption
                    current_hex = grid.get_hex_at_mouse(char_screen_pos, screen)
                    char_pos = list(current_hex)  # Update position
                    local_mv_limit = 99
                    path = a_star(current_hex, goal, grid.tiles, local_mv_limit)
                    if path:
                        queued_path = path
                        current_path_index = 0
                        grid.set_path_highlight(path)
                        is_moving = True
                        path_validated = False
                        data = {"action": "move_path", "start": current_hex, "goal": tuple(goal), "grid": grid.get_grid_state(), "game_mode": game_mode}
                        if not server_offline:
                            validation_thread = threading.Thread(target=validate_path_async, args=(data,))
                            validation_thread.daemon = True
                            validation_thread.start()
                        else:
                            path_validated = True
                        print(f"Exploration: switched to new path from current position")
                    else:
                        print("No path found!")
                else:  # Combat mode: original behavior for now, until CombatSystem is re-implemented correctly
                    if is_moving:
                        continue  # Can't plan new move during movement
                    # Calculate path from current position
                    start_hex = tuple(char_pos)
                    local_mv_limit = state.get_mv_limit()  # Use state method for mode-aware MV
                    # Block living enemy hexes to prevent occupation (DW: hexes occupied by one entity)
                    for enem in enemies:
                        if enem.hp > 0:
                            enemy_hex = tuple(enem.pos)
                            grid.tiles[enemy_hex].blocked = True
                    path = a_star(start_hex, goal, grid.tiles, local_mv_limit)
                    for enem in enemies:  # Reset
                        if enem.hp > 0:
                            enemy_hex = tuple(enem.pos)
                            grid.tiles[enemy_hex].blocked = False
                    if path:
                        grid.set_path_highlight(path)
                        planned_path = path
                        # Have enemies start their turn simultaneously in combat
                        for enem in enemies:
                            if enem.hp > 0:
                                enem.take_turn(list(enemies), char_pos, grid.tiles)
                        data = {"action": "move_path", "start": start_hex, "goal": tuple(goal), "grid": grid.get_grid_state(), "game_mode": game_mode}
                        validation_thread = threading.Thread(target=validate_combat_path_async, args=(path, data))
                        validation_thread.daemon = True
                        validation_thread.start()
                        print("Combat: planned path set, validating async")
                    else:
                        print("No path found!")
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_c:
                game_mode = 'combat'
                if is_moving:
                    is_moving = False
                last_cr_start = current_time
                combat_round = 0
                print("Switched to combat mode")
            elif event.key == pygame.K_e:
                game_mode = 'exploration'
                if queued_path and path_validated and not is_moving:
                    is_moving = True
                    current_path_index = 0
                print("Switched to exploration mode")



    # Handle rejected path flash
    if rejected_path and current_time - rejected_flash_time < FLASH_DURATION:
        for hex_pos in rejected_path:
            if tuple(hex_pos) in grid.tiles and not grid.tiles[tuple(hex_pos)].blocked:
                center = grid.hex_to_pixel(hex_pos[0], hex_pos[1])
                cx, cy = center[0] + screen.get_width() // 2, center[1] + screen.get_height() // 2
                pygame.draw.circle(screen, (255, 0, 0), (int(cx), int(cy)), grid.hex_size // 2, 2)
    else:
        if rejected_path:
            rejected_path = []

# Path-following movement handled by CombatSystem for lockstep execution
combat_system.update_positions(dt, grid.hex_size, screen, MOVE_SPEED)

# Enemy path-following movement and attacks
for enem in enemies:
    if enem.hp > 0:
        # Update enemy movement if they have a path
        if enem.is_moving and enem.queued_path and enem.current_path_index < len(enem.queued_path):
            enemy_path_complete = enem.update_movement(grid.hex_size, screen, MOVE_SPEED, dt)

            # Attack if path complete and within range
            if enemy_path_complete and enem.hp > 0:
                dist = hex_distance(enem.pos[0], enem.pos[1], char_pos[0], char_pos[1])
                if not state.defeated and (dist == 1 or (dist <= 3 and ENEMY_RANGED_ATTACK_ENABLED)):  # No more attacks on dead player
                    if dist == 1:
                        damage = roll_d6()
                        msg = f"Enemy melee attack for {damage}!"
                    else:
                        damage = max(0, roll_d6() - (dist - 1))
                        msg = f"Enemy ranged attack for {damage} (distance {dist})!"
                    if damage:
                        state.update_hp(damage)  # Update via GameState to sync HP
                        attack_indicators.append((tuple(enem.screen_pos), tuple(char_screen_pos), current_time))
                        print(f"{msg} Player HP: {state.player_hp}")


# Combat round tick: Execute planned actions via CombatSystem
if game_mode == 'combat' and (current_time - last_cr_start >= TICK_TIME):
    combat_system.execute_round_tick()

    # Enemy AI: Use AISystem for modular behavior, only in combat mode to reduce spam
    if game_mode == 'combat':
        ai_system.update_ai(enemies, char_pos)

# Draw
screen.fill((0, 0, 0))
grid.draw(screen)

char_renderer.draw_character(screen, int(char_screen_pos[0]), int(char_screen_pos[1]))

# Draw death overlay if player is dead
if state.defeated:
    dead_overlay = pygame.Surface((32, 32))
    dead_overlay.fill((100, 100, 100))
    dead_overlay.set_alpha(150)
    screen.blit(dead_overlay, (int(char_screen_pos[0] - 16), int(char_screen_pos[1] - 16)))

# Draw enemies
for enem in enemies:
    if enem.hp > 0:
        enem.draw(screen, dt)

# Draw health bars (now pulls from state with ActorStats backing)
draw_health_bar(screen, int(char_screen_pos[0]), int(char_screen_pos[1]), state.player_hp, state.max_player_hp)
for enem in enemies:
    if enem.hp > 0:
        draw_health_bar(screen, int(enem.screen_pos[0]), int(enem.screen_pos[1]), enem.hp, enem.max_hp)

# Draw attack indicators
for attacker_pos, victim_pos, start_time in attack_indicators.copy():
    if current_time - start_time > 5:
        attack_indicators.remove((attacker_pos, victim_pos, start_time))
    else:
        # Check if this is an enemy attack (based on position matching an enemy)
        is_enemy_attack = False
        for enem in enemies:
            if enem.hp > 0 and tuple(enem.screen_pos) == attacker_pos:
                is_enemy_attack = True
                enem.renderer.draw_attack_arrow(screen, attacker_pos, victim_pos, color=(255, 100, 100))
                break
        
        # If not an enemy attack, draw with default method
        if not is_enemy_attack:
            draw_attack_arrow(screen, attacker_pos, victim_pos, color=(200, 200, 200))



# Draw quest goal star (yellow polygon; references hex_to_screen)
goal_screen = hex_to_screen(goal_pos[0], goal_pos[1], grid.hex_size, screen)
pygame.draw.polygon(screen, (255, 255, 0), [  # Yellow star for goal
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
if game_mode == 'combat':
    clock_x, clock_y = SCREEN_WIDTH - 60, 60  # Top-right corner
    size = 30  # Size of hourglass
    elapsed = min(TICK_TIME, current_time - last_cr_start)
    progress = elapsed / TICK_TIME
    draw_sand_clock(screen, clock_x, clock_y, size, progress, font, state.combat_round)

    # Draw combat UI (HP bars, engagement highlights; references draw_sand_clock for consistent draw order)
    # Commented out for multiple enemies - need to update the UI to handle list
    # draw_combat_ui(screen, font, player_hp, 10, enemy.hp, enemy_max_hp, tuple(char_pos), tuple(enemy.pos), tuple(char_screen_pos), tuple(enemy.screen_pos))

# Draw rejected message if active
if rejected_message and (current_time - rejected_message_time < MESSAGE_DURATION):
    rejected_text_surface = font.render(rejected_message, True, (255, 0, 0)) # Red text
    text_rect = rejected_text_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 100))
    screen.blit(rejected_text_surface, text_rect)

# Draw win message if active (references rejected_message display)
if win_message and (current_time - win_message_time < state.WIN_DURATION):
    win_text_surface = font.render(win_message, True, (0, 255, 0)) # Green text
    text_rect = win_text_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 150))
    screen.blit(win_text_surface, text_rect)

# Draw tutorial text
mode_text = font.render(f"Mode: {game_mode} (E: exploration, C: combat)", True, (255, 255, 255))
screen.blit(mode_text, (10, 10))
tutorial_text = font.render("Left-click a hex to queue movement. Server validates on click and starts movement if approved.", True, (255, 255, 255))
screen.blit(tutorial_text, (10, 30))
quit_text = font.render("Close window to quit. Server logs moves.", True, (255, 255, 255))
screen.blit(quit_text, (10, 50))

pygame.display.flip()

pygame.quit()
