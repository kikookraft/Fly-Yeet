import random

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
            width: int = 3000,
            height: int = 1500,
            fps: int = 100) -> None:
        self.current_fps: float = 0
        self.width: int = width
        self.height: int = height
        self.fps: int = fps
        self.screen: pygame.Surface = pygame.display.set_mode(
            (self.width, self.height), pygame.NOFRAME)
        self.clock: pygame.time.Clock = pygame.time.Clock()
        pygame.display.set_caption("Fly YEEET")
        self.background_tile: pygame.Surface = pygame.image.load(
            "assets/tile.png").convert()
        self.background: pygame.Surface = pygame.Surface(
            (self.width, self.height))
        for x in range(0, self.width, self.background_tile.get_width()):
            for y in range(0, self.height, self.background_tile.get_height()):
                self.background.blit(self.background_tile, (x, y))

    def update(self) -> None:
        pygame.display.flip()
        self.screen.blit(self.background, (0, 0))
        self.clock.tick(self.fps)
        self.current_fps = math.floor(self.clock.get_fps())

    def get_fps(self) -> float:
        return self.current_fps


class Text:
    def __init__(self,
                 x: float,
                 y: float,
                 size: int,
                 text: str,
                 color: tuple[int, int, int] = (255, 255, 255)) -> None:
        self.x: float = x
        self.y: float = y
        self.size: int = size
        self.text: str = text
        self.font: pygame.font.Font = pygame.font.SysFont(None, self.size)
        self.text_surface: pygame.Surface = self.font.render(
            self.text, True, color)

    def draw(self, screen: pygame.Surface) -> None:
        screen.blit(self.text_surface, (self.x, self.y))

    def set_text(self, text: str) -> None:
        if text != self.text:
            self.text = text
            self.text_surface = self.font.render(
                self.text, True, (255, 255, 255))

    def set_size(self, size: int) -> None:
        self.size = size
        self.font = pygame.font.SysFont(None, self.size)
        self.text_surface = self.font.render(self.text, True, (255, 255, 255))

    def set_color(self, color: tuple[int, int, int]) -> None:
        self.text_surface = self.font.render(self.text, True, color)


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

    def move(self, x: float, y: float) -> None:
        self.x = x
        self.y = y


class Rect:
    def __init__(self,
                 x: float,
                 y: float,
                 width: float,
                 height: float,
                 radius: int = 0,
                 color: tuple[int, int, int] = (50, 150, 70),
                 alpha: int = 255,
                 debug: bool = False) -> None:
        self.x: float = x
        self.y: float = y
        self.z: float = 0  # rotation -- looking up by default
        self.vel_x: float = 0
        self.vel_y: float = 0
        self.vel_z: float = 0
        self.width: float = width
        self.height: float = height
        self.color: tuple[int, int, int] = color
        self.alpha: int = alpha
        self.is_mooving: bool = False
        self.target_x: float = x
        self.target_y: float = y
        self.target_z: float = self.z
        self.friction: float = .7
        self.move_power: float = 1.5
        self.radius: int = radius
        self.debug: bool = debug
        self.rect: pygame.Surface = pygame.Surface(
            (self.width, self.height), pygame.SRCALPHA)
        if debug:
            self.debug_img: pygame.Surface = pygame.transform.scale(
                pygame.image.load("assets/up.png").convert_alpha(),
                (int(self.width), int(self.height)))
            self.rotated_img: pygame.Surface = self.debug_img
        else:
            self.rotated_img: pygame.Surface = self.rect

    def center(self) -> tuple[float, float]:
        return (self.x - self.width / 2, self.y - self.height / 2)

    def rotate(self, angle: float) -> None:
        self.z = angle

    def get_pos(self) -> tuple[float, float]:
        return (self.x, self.y)

    def rotate_focus(self, x: float, y: float) -> None:
        """make the object rotate to face a specific point"""
        self.target_z = math.atan2(y - self.center()[1], x - self.center()[0])

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

    def handle_moves(self) -> None:
        diff_x: float = self.target_x - self.x  # distance
        diff_y: float = self.target_y - self.y
        diff_z: float = (self.target_z - self.z + math.pi) % (
            2 * math.pi) - math.pi  # shortest angular diatnce
        self.vel_x += diff_x * 0.05 * self.move_power  # velocity
        self.vel_y += diff_y * 0.05 * self.move_power
        self.vel_z += diff_z * 0.05 * self.move_power
        self.vel_x *= self.friction  # friction (limit wobble)
        self.vel_y *= self.friction
        self.vel_z *= self.friction
        self.x += self.vel_x  # update position
        self.y += self.vel_y
        self.rotate(self.z + self.vel_z)

        # Snap when movement finished
        if (abs(diff_x) < 0.5 and abs(diff_y) < 0.5 and abs(diff_z) < 0.5 and
                abs(self.vel_x) < 0.5 and abs(self.vel_y) < 0.5 and abs(self.vel_z) < 0.5):
            self.x = self.target_x
            self.y = self.target_y
            self.z = self.target_z
            self.vel_x, self.vel_y, self.vel_z = 0, 0, 0
            self.is_mooving = False

        if self.debug:
            # draw a line to see the destination
            pygame.draw.line(window.screen,
                             (255, 255, 255),
                             self.get_pos(),  # type:ignore
                             (self.target_x, self.target_y))

    def draw(self, screen: pygame.Surface) -> None:
        if self.is_mooving:
            self.handle_moves()
        if self.radius:
            # if recthas radius, create a rect inside
            # surface to have rounded corner
            self.rect.fill((0, 0, 0, 0))
            pygame.draw.rect(self.rect,
                             (self.color[0],
                              self.color[1],
                              self.color[2],
                              self.alpha),
                             (0, 0, self.width,
                              self.height),
                             border_radius=self.radius)
        else:
            self.rect.fill((self.color[0],
                            self.color[1],
                            self.color[2],
                            self.alpha))
        if self.debug:
            self.rect.blit(self.debug_img, (0, 0))
        self.rotated_img = pygame.transform.rotate(
            self.rect, (self.z * -57.2958) - 90)  # Convert radians to deg
        new_rect: pygame.Rect = self.rotated_img.get_rect(
            center=(self.x, self.y))
        screen.blit(self.rotated_img, new_rect.topleft)


class Drone(Rect):
    _rotation_cache: dict[str, dict[int, pygame.Surface]] = {}

    def __init__(self,
                 x: float,
                 y: float,
                 debug: bool,
                 cooldown: float = .5,
                 image_path: str = "assets/drone2.png") -> None:
        super().__init__(x, y, 50, 50, alpha=255, debug=debug)
        self.friction = .9
        self.move_power = 0.1
        self.wander_margin: float = .8
        self.moove_cooldown: float = cooldown
        self.last_mooved: float = 0
        self.scale: float = 3.0
        self.image_path: str = image_path

        # Initialize dictionary of 360 rotated versions ONCE for each image
        # this allow to avoid calling pygame.rotate for every images
        if image_path not in Drone._rotation_cache:
            Drone._rotation_cache[image_path] = {}
            base_img = pygame.transform.scale(
                pygame.image.load(image_path).convert_alpha(),
                (int(self.width * self.scale),
                    int(self.height * self.scale)))
            for angle in range(360):
                Drone._rotation_cache[image_path][angle] = \
                    pygame.transform.rotate(base_img, angle)

    def move(self, x: float, y: float) -> None:
        self.last_mooved = pygame.time.get_ticks() / 1000
        return super().move(x, y)

    def handle_collisions(
            self,
            all_drones: list["Drone"],
            window_width: int,
            window_height: int) -> None:
        hitbox_radius: float = 100  # Safe distance between drones

        # Border collision
        border_radius: float = hitbox_radius / 2.0
        if self.x < border_radius:
            self.vel_x += (border_radius - self.x) * 0.2
            self.is_mooving = True
        elif self.x > window_width - border_radius:
            self.vel_x -= (self.x - (window_width - border_radius)) * 0.2
            self.is_mooving = True

        if self.y < border_radius:
            self.vel_y += (border_radius - self.y) * 0.2
            self.is_mooving = True
        elif self.y > window_height - border_radius:
            self.vel_y -= (self.y - (window_height - border_radius)) * 0.2
            self.is_mooving = True

        for other in all_drones:  # collision with other
            if other is self:
                continue

            dx: float = self.x - other.x
            dy: float = self.y - other.y
            dist: float = math.hypot(dx, dy)
            if dist < hitbox_radius:
                if dist == 0:
                    # drone have the exact same pos, nudge them apart
                    dx = random.uniform(-1, 1)
                    dy = random.uniform(-1, 1)
                    dist = math.hypot(dx, dy) or 1.0

                overlap: float = hitbox_radius - dist  # how much they overlap
                nx: float = dx / dist  # calculate direction
                ny: float = dy / dist
                force: float = overlap * 0.2  # transfer force
                self.vel_x += nx * force
                self.vel_y += ny * force
                self.is_mooving = True  # continue physics for both of them
                other.is_mooving = True

    def wander(self, window: Window) -> None:
        if pygame.time.get_ticks() / 1000 - \
                self.last_mooved > self.moove_cooldown:
            # find a random position and go to it
            self.move(
                (random.random() * self.wander_margin * window.width + (
                    window.width * (1-self.wander_margin)) / 2),
                (random.random() * self.wander_margin * window.height + (
                    window.height * (1-self.wander_margin)) / 2))

    def draw(self, screen: pygame.Surface) -> None:
        if self.is_mooving:
            self.handle_moves()

        # Fetch the pre-rotated image directly from cache in O(1) time
        degrees: int = int((self.z * -57.2958) - 90) % 360
        self.rotated_img = Drone._rotation_cache[self.image_path][degrees]

        new_rect: pygame.Rect = self.rotated_img.get_rect(
            center=(self.x, self.y))
        screen.blit(self.rotated_img, new_rect.topleft)


if __name__ == "__main__":
    window = Window()
    running = True
    stick = False
    objects: list[any] = [
        Drone(100, 100, debug=True, image_path="assets/drone.png")]
    objects.append(ImageObject(
        "assets/logo.png", window.width/2, 100, scale=1))
    objects.append(Rect(30, 30, 0, 0, radius=0, color=(255, 255, 255)))
    drones: list[Drone] = [Drone(
        300, 300, debug=True, cooldown=random.uniform(0.1, 2.0),
        image_path="assets/drone2.png"
        ) for _ in range(10)]
    fps = Text(10, 10, 24, "FPS: 0")
    drones_count = Text(10, 40, 24, f"Drones: {len(drones)}")
    while running:
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                    running = False
                if event.key == pygame.K_p:
                    stick: bool = not stick
                if event.key == pygame.K_d:
                    objects[0].debug = not objects[0].debug
                    if objects[0].debug:
                        objects[0].color = (255, 255, 255)
                        objects[0].alpha = 0
                    else:
                        objects[0].color = (50, 150, 70)
                        objects[0].alpha = 255
                if event.key == pygame.K_c:
                    drones.extend([Drone(
                        300, 300, debug=True, cooldown=random.uniform(0.1, 2.0)
                    ) for _ in range(10)])
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left mouse button
                    objects[0].move(event.pos[0], event.pos[1])
                    objects[2].radius = 15
                    objects[2].width = 30
                    objects[2].height = 30
                    objects[2].tp(event.pos[0], event.pos[1])
            if stick:
                objects[0].move(pygame.mouse.get_pos()[0],
                                pygame.mouse.get_pos()[1])
        all_game_drones = [objects[0]] + drones
        for d in all_game_drones:
            d.handle_collisions(all_game_drones, window.width, window.height)

        for obj in objects:
            obj.draw(window.screen)
        for drone in drones:
            drone.draw(window.screen)
            if pygame.time.get_ticks() / 1000 - drone.last_mooved > drone.moove_cooldown + 2:
                drone.wander(window)
        objects[1].dummy += 0.05
        objects[1].rotation = math.sin(objects[1].dummy) * 20
        if objects[2].radius > 0:
            objects[2].radius -= 1
            objects[2].width -= 2
            objects[2].height -= 2

        fps.set_text(f"FPS: {window.get_fps()}")
        drones_count.set_text(f"Drones: {len(drones)}")
        fps.draw(window.screen)
        drones_count.draw(window.screen)
        window.update()
    pygame.quit()
