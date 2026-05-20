import pygame
import math

pygame.init()
MOVE_POWER = 1
FRICTION = .9
CELLS = 25


def bezier(x: float) -> float:
    """calculate bezier curve for smooth moves or transitions"""
    return 3 * x**2 - 2 * x**3


class Window:
    def __init__(
            self,
            width: int = 1500,
            height: int = 900,
            fps: int = 60) -> None:
        self.width: int = width
        self.height: int = height
        self.fps: int = fps
        self.screen: pygame.Surface = pygame.display.set_mode(
            (self.width, self.height), pygame.NOFRAME)
        self.clock: pygame.time.Clock = pygame.time.Clock()
        pygame.display.set_caption("Fly YEEET")
        self.background_tile: pygame.Surface = pygame.image.load(
            "assets/tile.png").convert()

    def update(self) -> None:
        pygame.display.flip()
        self.screen.fill((20, 30, 60))
        for x in range(0, self.width, self.background_tile.get_width()):
            for y in range(0, self.height, self.background_tile.get_height()):
                self.screen.blit(self.background_tile, (x, y))
        self.clock.tick(self.fps)

    def change_res(self, width: int, height: int) -> None:
        self.width: int = width
        self.height: int = height
        self.screen: pygame.Surface = pygame.display.set_mode(
            (self.width, self.height), pygame.NOFRAME)


class ImageObject:
    def __init__(self, image_path: str, x: float, y: float, scale: float = 1) -> None:
        self.image: pygame.Surface = pygame.image.load(image_path).convert_alpha()
        self.x: float = x
        self.y: float = y
        self.scale: float = scale
        self.rotation: float = 0
        self.dummy: float = 0

    def draw(self, screen: pygame.Surface) -> None:
        rotated_image: pygame.Surface = pygame.transform.rotate(self.image, self.rotation)
        scaled_image: pygame.Surface = pygame.transform.scale(rotated_image, (int(rotated_image.get_width() * self.scale), int(rotated_image.get_height() * self.scale)))
        screen.blit(scaled_image, (self.x - scaled_image.get_width() / 2, self.y - scaled_image.get_height() / 2))

class Rect:
    def __init__(self, x: float, y: float, width: float, height: float) -> None:
        self.x: float = x
        self.y: float = y
        self.vel_x: float = 0
        self.vel_y: float = 0
        self.width: float = width
        self.height: float = height
        self.color: tuple = (50, 150, 70)
        self.is_mooving: bool = False
        self.target_x: float = x
        self.target_y: float = y
        self.friction: float = FRICTION

    def move(self, dx: float, dy: float, duration: float = 0.2) -> None:
        """Update the target to move towards. Velocity is inherited automatically."""
        self.is_mooving = True
        self.target_x: float = self.x + dx
        self.target_y: float = self.y + dy

    def fixed_move(self, x: float, y: float) -> None:
        """Move to a fixed position."""
        self.is_mooving = True
        self.target_x: float = x
        self.target_y: float = y

    def draw(self, screen: pygame.Surface) -> None:
        if self.is_mooving:
            # Calculate distance to new target
            diff_x: float = self.target_x - self.x
            diff_y: float = self.target_y - self.y
            
            # Add acceleration to current velocity (spring behavior)
            self.vel_x += diff_x * 0.05 * MOVE_POWER
            self.vel_y += diff_y * 0.05 * MOVE_POWER
            
            # Dampen velocity so it doesn't oscillate forever
            self.vel_x *= self.friction
            self.vel_y *= self.friction
            
            # Apply inherited velocity
            self.x += self.vel_x
            self.y += self.vel_y
            
            # Snap to target when it's settled down
            if abs(diff_x) < 0.5 and abs(diff_y) < 0.5 and abs(self.vel_x) < 0.5 and abs(self.vel_y) < 0.5:
                self.x = self.target_x
                self.y = self.target_y
                self.vel_x, self.vel_y = 0, 0
                self.is_mooving = False

        pygame.draw.rect(screen, self.color, (self.x - self.width / 2, self.y - self.height / 2, self.width, self.height))

if __name__ == "__main__":
    window = Window()
    running = True
    stick = False
    objects: list[Rect | ImageObject] = [Rect(100, 100, 50, 50)]
    objects.append(ImageObject("assets/logo.png", window.width/2, 100, scale=1))
    while running:
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_a:
                    objects[0].move(-100, 0, duration=0.2)
                if event.key == pygame.K_d:
                    objects[0].move(100, 0, duration=0.2)
                if event.key == pygame.K_w:
                    objects[0].move(0, -100, duration=0.2)
                if event.key == pygame.K_s:
                    objects[0].move(0, 100, duration=0.2)
                if event.key == pygame.K_p:
                    stick = not stick
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left mouse button
                    objects[0].move(event.pos[0] - objects[0].x, event.pos[1] - objects[0].y, duration=0.2)
            if stick:
                objects[0].fixed_move(pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1])
        for obj in objects:
            obj.draw(window.screen)
        objects[1].dummy += 0.05
        objects[1].rotation = math.sin(objects[1].dummy) * 20
        window.update()
    pygame.quit()