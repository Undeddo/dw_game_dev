import pygame
import random

def draw_sand_clock(screen, clock_x, clock_y, size, progress, font, combat_round):
    """Draw the combat sand clock (hourglass) with proper wide-top-narrow-middle-wide-bottom shape."""
    # Draw bottom triangle (pointing up: narrow at top, wide at bottom)
    bottom_points = [(clock_x - size//2, clock_y + 2*size + 10), (clock_x + size//2, clock_y + 2*size + 10), (clock_x, clock_y + size + 10)]
    pygame.draw.polygon(screen, (255, 255, 255), bottom_points, 2)  # White outline

    # Draw top triangle (pointing down: wide at top, narrow at bottom)
    top_points = [(clock_x - size//2, clock_y), (clock_x + size//2, clock_y), (clock_x, clock_y + size)]
    pygame.draw.polygon(screen, (255, 255, 255), top_points, 2)  # White outline

    # Draw sand in top chamber (decreasing as progress increases)
    if progress < 1:
        h_top = size * (1 - progress)
        y_top_fill = clock_y + size - h_top
        w_top = int(h_top)
        top_sand_points = [(clock_x, clock_y + size), (clock_x - w_top//2, y_top_fill), (clock_x + w_top//2, y_top_fill)]
        pygame.draw.polygon(screen, (255, 255, 0), top_sand_points)

    # Draw sand in bottom chamber (increasing as progress increases)
    if progress > 0:
        h_bottom = progress * size
        y_bottom_fill = clock_y + size + 10 + h_bottom
        w_bottom = int(h_bottom)
        bottom_sand_points = [(clock_x, clock_y + size + 10), (clock_x - w_bottom//2, y_bottom_fill), (clock_x + w_bottom//2, y_bottom_fill)]
        pygame.draw.polygon(screen, (255, 255, 0), bottom_sand_points)

    # Draw round text
    round_text = font.render(f"Round {combat_round}", True, (255, 255, 255))
    screen.blit(round_text, (clock_x - round_text.get_width()//2, clock_y + 2*size + 20))
