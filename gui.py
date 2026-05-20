import pygame
import math

pygame.init()
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
        for x in range(0, self.width, self.background_tile.get_width()):
            for y in range(0, self.height, self.background_tile.get_height()):
                self.screen.blit(self.background_tile, (x, y))
        self.clock.tick(self.fps)


class ImageObject:
    def __init__(self,
                 image_path: str,
                 x: float,
                 y: float,
                 scale: float = 1) -> None:
        self.image: pygame.Surface = pygame.image.load(
            image_path).convert_alpha()
        self.x: float = x
        self.y: float = y
        self.scale: float = scale
        self.rotation: float = 0
        self.dummy: float = 0

    def draw(self, screen: pygame.Surface) -> None:
        rotated_image: pygame.Surface = pygame.transform.rotate(
            self.image, self.rotation)
        scaled_image: pygame.Surface = pygame.transform.scale(
            rotated_image, (int(rotated_image.get_width() * self.scale),
                            int(rotated_image.get_height() * self.scale)))
        screen.blit(scaled_image, (
            self.x - scaled_image.get_width() / 2,
            self.y - scaled_image.get_height() / 2))


class Rect:
    def __init__(self,
                 x: float,
                 y: float,
                 width: float,
                 height: float,
                 radius: int = 0,
                 color: tuple[int, int, int] = (50, 150, 70)) -> None:
        self.x: float = x
        self.y: float = y
        self.rotation: float = 0  # looking up
        self.vel_x: float = 0
        self.vel_y: float = 0
        self.vel_z: float = 0
        self.width: float = width
        self.height: float = height
        self.color: tuple[int, int, int] = color
        self.is_mooving: bool = False
        self.target_x: float = x
        self.target_y: float = y
        self.target_z: float = self.rotation
        self.friction: float = .7
        self.move_power: float = 1.5
        self.radius: int = radius

    def center(self) -> tuple[float, float]:
        return (self.x - self.width / 2, self.y - self.height / 2)

    def rotate(self, angle: float) -> None:
        self.rotation = angle

    def rotate_focus(self, x: float, y: float) -> None:
        """make the object rotate to face a specific point"""
        dx: float = x - self.center()[0]
        dy: float = y - self.center()[1]
        self.target_z = math.atan2(dy, dx)

    def move_rel(self, dx: float, dy: float) -> None:
        """Update the target to move towards. Velocity is inherited"""
        self.is_mooving = True
        self.target_x: float = self.x + dx
        self.target_y: float = self.y + dy
        self.rotate_focus(self.target_x, self.target_y)

    def move(self, x: float, y: float) -> None:
        """Move to a fixed position."""
        self.is_mooving = True
        self.target_x: float = x
        self.target_y: float = y
        self.rotate_focus(self.target_x, self.target_y)

    def tp(self, x: float, y: float) -> None:
        """Teleport to a fixed position."""
        self.x = x
        self.y = y

    def draw(self, screen: pygame.Surface) -> None:
        if self.is_mooving:
            diff_x: float = self.target_x - self.x  # distance
            diff_y: float = self.target_y - self.y
            diff_z: float = self.target_z - self.rotation
            self.vel_x += diff_x * 0.05 * self.move_power  # velocity
            self.vel_y += diff_y * 0.05 * self.move_power
            self.vel_z += diff_z * 0.05 * self.move_power
            self.vel_x *= self.friction  # friction (limit wobble)
            self.vel_y *= self.friction
            self.vel_z *= self.friction
            self.x += self.vel_x  # update position
            self.y += self.vel_y
            self.rotate(self.target_z)

            # Snap when movement finished
            if abs(diff_x) < 0.5 and abs(diff_y) < 0.5 and abs(diff_z) < 0.5:
                self.x = self.target_x
                self.y = self.target_y
                self.vel_x, self.vel_y, self.vel_z = 0, 0, 0
                self.is_mooving = False

        if self.target_z != self.rotation:
            # create a surface
            surf: pygame.Surface = pygame.Surface((self.width, self.height),
                                                  pygame.SRCALPHA)
            surf.fill(self.color)
            rotated_img: pygame.Surface = pygame.transform.rotate(
                surf, self.rotation * 57.2958)  # Convert radians to degrees
            screen.blit(rotated_img, self.center())
        else:
            pygame.draw.rect(screen, self.color, (
                self.center()[0], self.center()[1],
                self.width, self.height), border_radius=self.radius)

class Drone(Rect):
    def __init__(self, x: float, y: float) -> None:
        super().__init__(x, y, 50, 50, color=(0, 255, 0))
        self.img: pygame.Surface = pygame.image.load(
            "assets/drone.png").convert_alpha()


if __name__ == "__main__":
    window = Window()
    running = True
    stick = False
    objects: list[Rect | ImageObject] = [Rect(100, 100, 50, 50)]
    objects.append(ImageObject("assets/logo.png", window.width/2, 100, scale=1))
    objects.append(Rect(30, 30, 0, 0, radius=0, color=(255, 255, 255)))
    while running:
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_a:
                    objects[0].move_rel(-100, 0)
                if event.key == pygame.K_d:
                    objects[0].move_rel(100, 0)
                if event.key == pygame.K_w:
                    objects[0].move_rel(0, -100)
                if event.key == pygame.K_s:
                    objects[0].move_rel(0, 100)
                if event.key == pygame.K_p:
                    stick = not stick
                if event.key == pygame.K_r:
                    window.change_res(500, 500)
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left mouse button
                    objects[0].move(event.pos[0], event.pos[1])
                    objects[2].radius = 15
                    objects[2].width = 30
                    objects[2].height = 30
                    objects[2].tp(event.pos[0], event.pos[1])
            if stick:
                objects[0].move(pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1])
        for obj in objects:
            obj.draw(window.screen)
        objects[1].dummy += 0.05
        objects[1].rotation = math.sin(objects[1].dummy) * 20
        if objects[2].radius > 0:
            objects[2].radius -= 1
            objects[2].width -= 2
            objects[2].height -= 2
        window.update()
    pygame.quit()
