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
from core.config import TICK_TIME, SERVER_URL
from utils.pathfinding import a_star
from utils.hex_utils import hex_distance
from utils.draw_utils import draw_sand_clock
from client.render.character_renderer import CharacterRenderer

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
char_pos = [0, 0]  # Current (q, r) as int list
char_screen_pos = [screen.get_width() // 2, screen.get_height() // 2]  # Screen position
queued_path = []  # List of (q,r)
current_path_index = 0
mv_limit = 6  # Default Mv/5ft per hex
game_mode = 'exploration'  # 'exploration' or 'combat'
path_validated = False  # True if server has approved the current path
initial_char_pos = None  # Initial char_pos for server validation to avoid interruptions
is_moving = False  # True if character is currently moving
goal_target = None  # Target goal for path validation
server_offline = False  # Flag to suppress repeated connection errors

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
                # Update if server's approved path differs from local (unlikely but possible)
                if approved_path != planned_path:
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



running = True
while running:
    dt = clock.tick(60) / 1000.0  # Delta time
    current_time = time.time()

    char_renderer.update(dt, is_moving)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
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
                else:  # Combat mode
                    # Calculate path from current position or end of round if moving
                    start_hex = tuple(queued_path[-1]) if is_moving and queued_path else tuple(char_pos)
                    local_mv_limit = mv_limit
                    path = a_star(start_hex, goal, grid.tiles, local_mv_limit)
                    if path:
                        grid.set_path_highlight(path)
                        planned_path = path
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

    # Path-following movement
    if is_moving and queued_path and current_path_index < len(queued_path):
        target_hex = queued_path[current_path_index]
        target_screen = hex_to_screen(target_hex[0], target_hex[1], grid.hex_size, screen)
        dx = target_screen[0] - char_screen_pos[0]
        dy = target_screen[1] - char_screen_pos[1]
        dist = math.hypot(dx, dy)
        if dist < 5:  # Reached target hex
            char_screen_pos = list(target_screen)
            char_pos = list(target_hex)
            current_path_index += 1
            print(f"Reached target hex: {target_hex}")
        else:
            # LERP towards target
            t = min(1.0, (MOVE_SPEED * dt) / dist)
            char_screen_pos[0] += dx * t
            char_screen_pos[1] += dy * t

    if queued_path and current_path_index >= len(queued_path):
        # Reached end of path
        queued_path = []
        current_path_index = 0
        is_moving = False  # No longer moving

    # Combat round tick: advance timer and start planned movement if applicable
    if game_mode == 'combat' and (current_time - last_cr_start >= TICK_TIME):
        last_cr_start += TICK_TIME  # Lockstep advance CR timer
        combat_round += 1
        if planned_path and not is_moving:
            queued_path = planned_path
            current_path_index = 0
            is_moving = True
            planned_path = None
            grid.set_path_highlight(queued_path)  # Ensure highlighted
            print("Combat CR tick: started planned movement")
        # CR advances even if no planned movement (no action)
    # Draw
    screen.fill((0, 0, 0))
    grid.draw(screen)

    char_renderer.draw_character(screen, int(char_screen_pos[0]), int(char_screen_pos[1]))

    # Draw combat sand clock and round counter
    if game_mode == 'combat':
        clock_x, clock_y = SCREEN_WIDTH - 60, 60  # Top-right corner
        size = 30  # Size of hourglass
        elapsed = min(TICK_TIME, current_time - last_cr_start)
        progress = elapsed / TICK_TIME
        draw_sand_clock(screen, clock_x, clock_y, size, progress, font, combat_round)

    # Draw rejected message if active
    if rejected_message and (current_time - rejected_message_time < MESSAGE_DURATION):
        rejected_text_surface = font.render(rejected_message, True, (255, 0, 0)) # Red text
        text_rect = rejected_text_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 100))
        screen.blit(rejected_text_surface, text_rect)

    # Draw tutorial text
    mode_text = font.render(f"Mode: {game_mode} (E: exploration, C: combat)", True, (255, 255, 255))
    screen.blit(mode_text, (10, 10))
    tutorial_text = font.render("Left-click a hex to queue movement. Server validates on click and starts movement if approved.", True, (255, 255, 255))
    screen.blit(tutorial_text, (10, 30))
    quit_text = font.render("Close window to quit. Server logs moves.", True, (255, 255, 255))
    screen.blit(quit_text, (10, 50))

    pygame.display.flip()

pygame.quit()
