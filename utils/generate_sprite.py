"""
Utility script to generate a basic placeholder character spritesheet.
In the grand scheme, this provides a simple way to create initial sprite assets for prototyping, which can be replaced with artist-drawn sprites later.
Dependencies: pygame, os.
"""

import pygame
import os

def generate_spritesheet():
    pygame.init()

    frame_count = 8
    frame_width = 64
    frame_height = 64
    sheet_width = frame_count * frame_width
    sheet_height = frame_height

    spritesheet = pygame.Surface((sheet_width, sheet_height), pygame.SRCALPHA)

    colors = [(255 - i*30, 100 + i*10, i*30) for i in range(frame_count)]  # Vary colors for visibility

    for i in range(frame_count):
        rect = pygame.Rect(i * frame_width, 0, frame_width, frame_height)
        pygame.draw.rect(spritesheet, colors[i], rect)
        # Add a simple "character" shape: a circle or cross
        center = (rect.centerx, rect.centery)
        pygame.draw.circle(spritesheet, (255, 255, 255), center, 20)
        pygame.draw.line(spritesheet, (0, 0, 0), (center[0] - 10, center[1]), (center[0] + 10, center[1]), 3)
        pygame.draw.line(spritesheet, (0, 0, 0), (center[0], center[1] - 10), (center[0], center[1] + 10), 3)

    output_dir = 'client/sprites'
    output_path = os.path.join(output_dir, 'character.png')
    os.makedirs(output_dir, exist_ok=True)
    pygame.image.save(spritesheet, output_path)
    pygame.quit()
    print(f"Basic spritesheet generated at {output_path}")

if __name__ == '__main__':
    generate_spritesheet()
