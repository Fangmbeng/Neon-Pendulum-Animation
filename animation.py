import pygame
import math
import random
import sys

# ------------------------- Constants -------------------------
WIDTH, HEIGHT = 800, 600
FPS = 60
TIME_LIMIT = 10  # seconds

# Pendulum parameters
PENDULUM_ANCHOR = (400, 100)
PENDULUM_LENGTH = 150
GRAVITY = 0.5            # pixels/frame²
DAMPING = 0.96           # direct multiplier (96% of velocity retained per frame)

# Hexagon parameters
HEXAGON_SIDE = 20        # side length (for a regular hexagon, side equals radius)
HEXAGON_ROTATION_SPEED = math.radians(3)  # 3º per frame in radians

# Neon trail parameters
TRAIL_LENGTH = 8         # frames of persistence

# Light beam parameters
LIGHT_BEAM_THRESHOLD = 5  # velocity threshold (in pixels/frame)
LIGHT_BEAM_SPREAD = math.radians(30)  # 30º total spread (±15º)
BEAM_COUNT = 6
BEAM_LENGTH = 100

# Grid parameters
GRID_SPACING = 15
GRID_WARP_RADIUS = 150  # radius around the pendulum bob where grid warps

# Vortex parameters
NUM_VORTEX_PARTICLES = 100
VORTEX_ROTATION_SPEED = 0.02  # rad/frame (clockwise)
VORTEX_CENTER = (WIDTH // 2, HEIGHT // 2)

# Colors (RGB)
BLACK = (0, 0, 0)
CYAN = (0, 255, 255)
PURPLE = (128, 0, 128)
WHITE = (255, 255, 255)

# ------------------------- Pygame Setup -------------------------
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pendulum Animation")
clock = pygame.time.Clock()

# ------------------------- Utility Functions -------------------------
def interpolate_color(c1, c2, t):
    """Linearly interpolate between colors c1 and c2 (t from 0 to 1)."""
    return (int(c1[0]*(1-t) + c2[0]*t),
            int(c1[1]*(1-t) + c2[1]*t),
            int(c1[2]*(1-t) + c2[2]*t))

# ------------------------- Pendulum & Hexagon Setup -------------------------
# Initial pendulum state
angle = math.pi / 4  # initial angle (45º from vertical)
angular_velocity = 0
angular_acceleration = 0

# Hexagon: compute local coordinates of a regular hexagon centered at (0,0)
hexagon_points = []
for i in range(6):
    theta = math.radians(60 * i)
    x = HEXAGON_SIDE * math.cos(theta)
    y = HEXAGON_SIDE * math.sin(theta)
    hexagon_points.append((x, y))
hexagon_angle = 0  # starting rotation

# ------------------------- Trail Setup -------------------------
# Stores the last TRAIL_LENGTH bob positions for the neon trail
trail = []

# ------------------------- Vortex Setup -------------------------
# Create NUM_VORTEX_PARTICLES particles with a random starting angle and radius ~100px
vortex_particles = []
for _ in range(NUM_VORTEX_PARTICLES):
    particle_angle = random.uniform(0, 2 * math.pi)
    particle_radius = random.uniform(90, 110)  # around 100 px
    vortex_particles.append({"angle": particle_angle, "radius": particle_radius})

# ------------------------- Drawing Functions -------------------------
def draw_hexagon(surface, center, angle, color):
    """Draws a rotated hexagon with its center at 'center'."""
    rotated_points = []
    for x, y in hexagon_points:
        rx = x * math.cos(angle) - y * math.sin(angle)
        ry = x * math.sin(angle) + y * math.cos(angle)
        rotated_points.append((center[0] + rx, center[1] + ry))
    pygame.draw.polygon(surface, color, rotated_points)

def draw_neon_trail(surface, trail_points):
    """Draws an 8-frame neon trail that gradients from PURPLE (old) to CYAN (new)."""
    if len(trail_points) < 2:
        return
    # Create a temporary surface for alpha-blended drawing.
    trail_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    n = len(trail_points)
    for i in range(n - 1):
        # t=0 for oldest, t=1 for newest
        t = i / (n - 1)
        color = interpolate_color(PURPLE, CYAN, t)
        # Fade alpha with age (newer segments more opaque)
        alpha = int(255 * (i + 1) / n)
        color_with_alpha = (color[0], color[1], color[2], alpha)
        pygame.draw.line(trail_surf, color_with_alpha, trail_points[i], trail_points[i + 1], 3)
    surface.blit(trail_surf, (0, 0))

def draw_light_beams(surface, center, count=BEAM_COUNT, length=BEAM_LENGTH):
    """Draws semi-transparent radial light beams with a 30º spread from 'center'."""
    beams_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    half_spread = LIGHT_BEAM_SPREAD / 2  # ±15º
    for i in range(count):
        central_angle = i * (2 * math.pi / count)
        angle1 = central_angle - half_spread
        angle2 = central_angle + half_spread
        point1 = center
        point2 = (center[0] + length * math.cos(angle1),
                  center[1] + length * math.sin(angle1))
        point3 = (center[0] + length * math.cos(angle2),
                  center[1] + length * math.sin(angle2))
        pygame.draw.polygon(beams_surf, (255, 255, 255, 80), [point1, point2, point3])
    surface.blit(beams_surf, (0, 0))

def draw_warped_grid(surface, warp_center, warp_radius=GRID_WARP_RADIUS):
    """Draws a grid with 15px spacing; points within 'warp_radius' of warp_center are snapped to concentric circles."""
    grid_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for x in range(0, WIDTH, GRID_SPACING):
        for y in range(0, HEIGHT, GRID_SPACING):
            dx = x - warp_center[0]
            dy = y - warp_center[1]
            r = math.hypot(dx, dy)
            if r < warp_radius and r != 0:
                theta = math.atan2(dy, dx)
                new_r = round(r / GRID_SPACING) * GRID_SPACING
                new_x = warp_center[0] + new_r * math.cos(theta)
                new_y = warp_center[1] + new_r * math.sin(theta)
                pygame.draw.circle(grid_surf, (50, 50, 50, 150), (int(new_x), int(new_y)), 2)
            else:
                pygame.draw.circle(grid_surf, (50, 50, 50, 150), (x, y), 1)
    surface.blit(grid_surf, (0, 0))

def update_and_draw_vortex(surface, particles, center):
    """Updates and draws the vortex particles as 1px white dots."""
    for p in particles:
        # Update the angle for clockwise swirl (subtracting angle)
        p["angle"] -= VORTEX_ROTATION_SPEED
        x = center[0] + p["radius"] * math.cos(p["angle"])
        y = center[1] + p["radius"] * math.sin(p["angle"])
        pygame.draw.circle(surface, WHITE, (int(x), int(y)), 1)

# ------------------------- Main Animation Loop -------------------------
running = True
start_ticks = pygame.time.get_ticks()

while running:
    clock.tick(FPS)
    
    # Handle events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Clear the canvas
    screen.fill(BLACK)
    
    # ----------------- Update Pendulum Physics -----------------
    angular_acceleration = (-GRAVITY / PENDULUM_LENGTH) * math.sin(angle)
    angular_velocity += angular_acceleration
    angular_velocity *= DAMPING  # Apply 4% damping per frame
    angle += angular_velocity

    # Compute pendulum bob position
    bob_x = PENDULUM_ANCHOR[0] + PENDULUM_LENGTH * math.sin(angle)
    bob_y = PENDULUM_ANCHOR[1] + PENDULUM_LENGTH * math.cos(angle)
    bob = (bob_x, bob_y)
    
    # Draw the pendulum rod (cyan line)
    pygame.draw.line(screen, CYAN, PENDULUM_ANCHOR, bob, 2)

    # ----------------- Update Hexagon & Trail -----------------
    hexagon_angle += HEXAGON_ROTATION_SPEED  # Rotate hexagon 3º per frame
    draw_hexagon(screen, bob, hexagon_angle, CYAN)
    
    # Update neon trail (store the latest bob positions)
    trail.append(bob)
    if len(trail) > TRAIL_LENGTH:
        trail.pop(0)
    draw_neon_trail(screen, trail)

    # ----------------- Draw Light Beams -----------------
    # Compute the bob’s linear velocity (approximation)
    velocity = abs(angular_velocity) * PENDULUM_LENGTH
    if velocity > LIGHT_BEAM_THRESHOLD:
        draw_light_beams(screen, bob)

    # ----------------- Draw Warped Grid -----------------
    # Warp the grid points into concentric circles near the pendulum bob
    draw_warped_grid(screen, bob)
    
    # ----------------- Update and Draw Vortex -----------------
    update_and_draw_vortex(screen, vortex_particles, VORTEX_CENTER)
    
    # ----------------- Check Time Limit -----------------
    elapsed = (pygame.time.get_ticks() - start_ticks) / 1000.0
    if elapsed > TIME_LIMIT:
        running = False

    # Update the display
    pygame.display.flip()

pygame.quit()
sys.exit()
